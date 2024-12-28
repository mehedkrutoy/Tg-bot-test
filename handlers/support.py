from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from states.states import Form
from config.config import config
from keyboards.reply import get_end_chat_keyboard
from keyboards.inline import get_support_keyboard, get_start_keyboard
from keyboards.reply import get_main_menu_keyboard
from handlers.admin import is_moderator

router = Router()
support_chats = {}

@router.callback_query(F.data == "support")
async def show_support_info(callback: CallbackQuery):
    if not callback.message or not callback.bot:
        return
        
    support_text = """🧑‍💻 Часто задаваемые вопросы:

1. Почему так долго проверяют чек?
• Чеки проверяются в ручную, а не автоматически. До 24 часов занимает проверка чека.

2. Почему так долго выводят золото?
• Вывод золота занимает до 24 часов. Мы стараемся как можно быстрее вывести вам золото.

3. Безопасно ли у вас покупать?
• Вес товар получен честным путём. Если сомневаетесь в безопасности, лучше покупать в игре.

💡 Прежде чем задать вопрос, убедитесь что здесь нет ответа на ваш вопрос

Связаться - @pr1nce82"""

    await callback.bot.edit_message_text(
        text=support_text,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_support_keyboard()
    )

@router.callback_query(F.data == "start_support")
async def start_support_chat(callback: CallbackQuery, state: FSMContext):
    if not callback.from_user or not callback.message:
        return
        
    user_id = callback.from_user.id
    
    if user_id in config.MODERATOR_CHAT_IDS:
        await callback.message.answer("Вы модератор и не можете создать запрос в поддержку")
        return
        
    if user_id in support_chats:
        await callback.message.answer("У вас уже есть активный чат с поддержкой")
        return
        
    support_chats[user_id] = {
        "user_id": user_id,
        "username": callback.from_user.username or "Неизвестный пользователь"
    }
    
    await state.set_state(Form.in_support_chat)
    await callback.message.answer(
        "Чат с поддержкой создан. Отправьте ваше сообщение.",
        reply_markup=get_end_chat_keyboard()
    )

@router.message(Form.in_support_chat)
async def handle_support_message(message: Message, state: FSMContext):
    if not message.from_user or not message.bot:
        return
        
    user_id = message.from_user.id
    
    # Проверяем, активен ли чат
    if user_id not in support_chats:
        await state.clear()
        await message.answer(
            "Чат с поддержкой был завершен",
            reply_markup=get_start_keyboard()
        )
        return
        
    if message.text == "Завершить чат":
        await end_support_chat(user_id, state, message.bot)
        remove_keyboard = ReplyKeyboardMarkup(
            keyboard=[], resize_keyboard=True, remove_keyboard=True
        )
        await message.answer(
            "Чат с поддержкой завершен",
            reply_markup=remove_keyboard
        )
        await message.answer(
            "Выберите действие:",
            reply_markup=get_start_keyboard()
        )
        return

    # Пересылка сообщений модераторам
    for moderator_id in config.MODERATOR_CHAT_IDS:
        try:
            # Информация о пользователе
            user_info = (
                f"Сообщение от {message.from_user.username or 'Неизвестный'}\n"
                f"ID: {message.from_user.id}\n"
                f"Модератор: {config.MODERATOR_CHAT_IDS[moderator_id]}\n"
            )
            
            # Пересылаем разные типы сообщений
            if message.text:
                await message.bot.send_message(
                    moderator_id,
                    f"{user_info}\nТекст: {message.text}"
                )
            elif message.photo:
                await message.bot.send_photo(
                    moderator_id,
                    message.photo[-1].file_id,
                    caption=user_info
                )
            elif message.video:
                await message.bot.send_video(
                    moderator_id,
                    message.video.file_id,
                    caption=user_info
                )
            elif message.document:
                await message.bot.send_document(
                    moderator_id,
                    message.document.file_id,
                    caption=user_info
                )
            elif message.voice:
                await message.bot.send_voice(
                    moderator_id,
                    message.voice.file_id,
                    caption=user_info
                )
            elif message.sticker:
                # Сначала отправляем информацию о пользователе
                await message.bot.send_message(moderator_id, user_info)
                # Затем отправляем стикер
                await message.bot.send_sticker(
                    moderator_id,
                    message.sticker.file_id
                )
        except Exception as e:
            continue

async def end_support_chat(user_id: int, state: FSMContext, bot=None):
    if user_id in support_chats:
        # Уведомляем модераторов о завершении чата
        if bot:
            for moderator_id in config.MODERATOR_CHAT_IDS:
                try:
                    await bot.send_message(
                        moderator_id,
                        f"Пользователь {support_chats[user_id]['username']} (ID: {user_id}) завершил чат"
                    )
                except:
                    pass
        del support_chats[user_id]
    await state.clear()

@router.message(F.reply_to_message)
async def handle_moderator_reply(message: Message):
    if not message.from_user or not message.bot or not message.reply_to_message:
        return
        
    # Проверяем, является ли отправитель модератором или админом
    if not is_moderator(message.from_user.id):
        return
        
    try:
        # Ищем ID пользователя в тексте или подписи сообщения
        reply_text = message.reply_to_message.text or message.reply_to_message.caption
        if not reply_text:
            await message.answer("❌ Не удалось найти ID пользователя в сообщении")
            return
            
        # Извлекаем ID пользователя из текста сообщения
        user_id = int(reply_text.split("ID:")[1].split()[0])
        
        # Проверяем, активен ли чат с пользователем
        if user_id not in support_chats:
            await message.answer("❌ Чат с пользователем уже завершен")
            return
            
        # Определяем роль и имя отправителя
        if message.from_user.id in config.ADMIN_IDS:
            moderator_name = config.ADMIN_IDS[message.from_user.id]
        else:
            moderator_name = config.MODERATOR_CHAT_IDS[message.from_user.id]
            
        # Отправляем ответ пользователю в зависимости от типа сообщения
        prefix = f"Поддержка ({moderator_name}): "
        
        if message.text:
            await message.bot.send_message(user_id, f"{prefix}{message.text}")
        elif message.photo:
            await message.bot.send_photo(
                user_id,
                message.photo[-1].file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.video:
            await message.bot.send_video(
                user_id,
                message.video.file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.document:
            await message.bot.send_document(
                user_id,
                message.document.file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.voice:
            await message.bot.send_voice(
                user_id,
                message.voice.file_id,
                caption=prefix + (message.caption or "")
            )
        elif message.sticker:
            await message.bot.send_sticker(user_id, message.sticker.file_id)
            
        await message.answer("✅ Сообщение отправлено пользователю")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке сообщения: {str(e)}") 