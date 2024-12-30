from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import LabeledPrice
from typing import Union

from keyboards.inline import get_start_keyboard, get_payment_methods_keyboard, get_profile_keyboard, get_back_to_menu_keyboard
from keyboards.reply import get_main_menu_keyboard
from states.states import Form, ReplenishStates, NumberInput
from database.methods import (
    get_user_balance, 
    get_user_profile, 
    get_user, 
    register_user,
    check_used_promo,
    activate_promo_code,
    has_used_any_promo,
    check_promo_code,
    use_promo_code,
    update_balance
)
from config.config import config

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    if not message.from_user or not message.text or not message.bot:
        return
        
    args = message.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            # Проверяем, существует ли реферер
            referrer = await get_user(referrer_id)
            if not referrer or int(str(referrer.user_id)) == message.from_user.id:
                referrer_id = None
        except ValueError:
            referrer_id = None
            
    # ����егистрируем пользователя
    await register_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        referrer_id=referrer_id
    )
    
    await message.answer(
        "👋 Добро пожаловать в бота!\n"
        "Выберите действие:",
        reply_markup=get_start_keyboard()
    )

        

@router.message(Command("hui"))
async def hui(message: Message):
    await message.answer("""
████╗░░░████████████╗
████║░░░████████████║
████║░░░████╔═══════╝
████║░░░████║░░░░░░░░
████████████████████╗
████████████████████║
╚═══════████╔═══████║
░░░░░░░░████║░░░████║
████████████║░░░████║
████████████║░░░��███║
╚═══════════╝░░░╚═══╝
""")


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    if not callback.from_user or not callback.message or not callback.bot:
        return
        
    user_data = await get_user_profile(callback.from_user.id)
    if user_data:
        balance, total_referrals = user_data
        ref_link = f"https://t.me/{(await callback.bot.me()).username}?start={callback.from_user.id}"
        
        profile_text = f"""👤 Ваш профиль:
        
💰 Баланс: {balance} RUB
👥 Рефералов: {total_referrals}

🔗 Ваша реферальная ссылка:
{ref_link}

💎 За каждого приглашенного пользователя вы получаете 5% от его пополнений!"""

        await callback.bot.edit_message_text(
            text=profile_text,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=get_profile_keyboard(callback.from_user.id)
        )
    else:
        await callback.answer("Не удалось загрузить данные профиля", show_alert=True)

@router.callback_query(F.data == "calculator")
async def handle_calculator(callback: CallbackQuery, state: FSMContext):
    if not callback.message or not callback.bot:
        return
        
    await callback.message.answer(
        "Введите число для умножения:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id
    )
    await state.set_state(NumberInput.waiting_for_number)

@router.message(NumberInput.waiting_for_number)
async def process_number(message: Message, state: FSMContext):
    if not message.text:
        return
        
    try:
        value = float(message.text.replace(",", "."))
        result = config.COURSE_RATE * value
        await message.answer(
            f"Результат: {result}",
            reply_markup=get_main_menu_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "Пожалуйста, введите корректное число.",
            reply_markup=get_main_menu_keyboard()
        )

@router.message(F.text == "🔙 Главное меню")
async def handle_main_menu_button(message: Message):
    if not message.from_user:
        return
        
    await message.answer(
        "👋 Выберите действие:",
        reply_markup=get_start_keyboard()
    )

@router.callback_query(F.data == "news")
async def show_news(callback: CallbackQuery):
    if not callback.message or not callback.bot:
        return
    await callback.bot.edit_message_text(
        text=f"Наш новостной канал: {config.GROUP_NEWS}",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_start_keyboard()
    )

@router.callback_query(F.data == "reviews")
async def show_reviews(callback: CallbackQuery):
    if not callback.message or not callback.bot:
        return
    await callback.bot.edit_message_text(
        text=f"Наши отзывы: {config.GROUP_REVIEWS}",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_start_keyboard()
    )

@router.callback_query(F.data == "course")
async def show_course(callback: CallbackQuery):
    if not callback.message or not callback.bot:
        return
    await callback.bot.edit_message_text(
        text=f"Текущий курс: {config.COURSE_RATE}",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_start_keyboard()
    )

@router.callback_query(F.data == "withdraw")
async def show_withdraw(callback: CallbackQuery):
    if not callback.message or not callback.bot:
        return
    await callback.bot.edit_message_text(
        text="Для вывода средств обратитесь в поддержку",
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        reply_markup=get_back_to_menu_keyboard()
    )

@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()  # Очищаем состояние
    await callback.message.answer(
        "👋 Добро пожаловать в бота!\nВыберите действие:",
        reply_markup=get_start_keyboard()  # Отправляем главное меню
    )

# @router.message(F.text.startswith("PROMO_"))
# async def activate_promo(message: Message):
#     if not message.from_user:
#         return
        
#     promo_code = message.text.strip()
#     user_id = message.from_user.id

#     # Проверяем наличие промокода в базе данных
#     promo_data = await check_promo_code(promo_code, user_id)
    
#     if not promo_data:
#         await message.answer("❌ Промокод недействителен или уже был использован.")
#         return

#     # Если промокод действителен, активируем его
#     bonus_amount = promo_data['amount']
    
#     # Записываем использование промокода
#     await use_promo_code(user_id, promo_code)

#     # Обновляем баланс пользователя
#     await update_balance(user_id, bonus_amount)

#     await message.answer(f"✅ Промокод успешно активирован!\nНа ваш баланс начислено {bonus_amount} RUB")

@router.message(Command("1"))
async def send_sticker(message: Message):
    sticker_id = "CAACAgIAAxkBAAENZPtnbcKQce9Qv-16VAXk7lBfiJJ5GgAC_x8AAsqp2Eho4h_hqzosBTYE"  # Замените на ваш ID стикера
    await message.answer_sticker(sticker_id) 

# Обработчик для неизвестных команд и сообщений
@router.message()
async def unknown_command(message: Message):
    await message.answer("❌ Эта команда не существует. Пожалуйста, используйте доступные команды.") 

@router.callback_query(F.data == "activate_promo")
async def activate_promo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.waiting_for_promo)  # Устанавливаем состояние ожидания ввода промокода
    await callback.message.answer("Введите ваш промокод:")

@router.message(Form.waiting_for_promo)
async def process_promo(message: Message, state: FSMContext):
    promo_code = message.text.strip()  # Получаем введенный промокод
    user_id = message.from_user.id

    # Проверяем наличие промокода в базе данных
    promo_data = await check_promo_code(promo_code, user_id)
    
    if not promo_data:
        await message.answer("❌ Промокод недействителен или уже был использован.")
        await state.clear()  # Очищаем состояние
        return

    # Если промокод действителен, активируем его
    bonus_amount = await activate_promo_code(user_id, promo_code)

    if bonus_amount is not None:
        await message.answer(f"✅ Промокод успешно активирован!\nНа ваш баланс начислено {bonus_amount} RUB")
    else:
        await message.answer("❌ Произошла ошибка при активации промокода.")
    
    await state.clear()  # Завершаем ожидание ввода промокода 