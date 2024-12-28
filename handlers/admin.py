from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from database.methods import (
    get_user_balance, 
    get_user_profile, 
    create_promo_code, 
    get_all_users, 
    update_balance,
    use_promo_code
)
from config.config import config
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from states.states import Form
import sys
import os
from restart import restart_bot
from aiogram.fsm.state import State, StatesGroup
import logging
from aiogram.fsm.storage.base import StorageKey
import asyncio

logger = logging.getLogger(__name__)

router = Router()

# Добавляем ADMIN_IDS
ADMIN_IDS = config.ADMIN_IDS.keys()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def is_moderator(user_id: int) -> bool:
    return user_id in config.MODERATOR_CHAT_IDS or user_id in ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
        
    await message.answer(
        "👨‍💼 Админ-панел\n"
        "Доступные команды:\n"
        "/broadcast - Рассылка\n"
        "/create_promo - Создать промокод\n"
        "/stats - Статистика\n"
        "/add_mod - Добавить модератора\n"
        "/remove_mod - Удалить модератора\n"
        "/list_mods - Список модераторов\n"
        "/clear_balance - Очистить баланс пользователя\n"
        "/restart - Перезапустить бота"
    )

@router.message(Command("create_promo"))
async def create_promo(message: Message):
    if not message.from_user or not is_admin(message.from_user.id) or not message.text:
        return
        
    args = message.text.split()
    if len(args) != 5:
        await message.answer(
            "Использование: /create_promo <код> <сумма/процент> "
            "<количество использований> <тип: sum/percent>"
        )
        return
        
    try:
        code = args[1]
        amount = float(args[2])
        uses = int(args[3])
        promo_type = args[4]
        
        if promo_type not in ['sum', 'percent']:
            raise ValueError("Неверный тип промокода")
            
        is_percentage = promo_type == 'percent'
        
        if is_percentage and (amount <= 0 or amount > 100):
            await message.answer("Процент должен быть от 1 до 100")
            return
            
        success = await create_promo_code(code, amount, uses, is_percentage)
        
        if success:
            await message.answer(
                f"✅ Промокод создан:\n"
                f"Код: {code}\n"
                f"{'Процент' if is_percentage else 'Сумма'}: {amount}\n"
                f"Количество использований: {uses}"
            )
        else:
            await message.answer("❌ Ошибка при создании промокода")
            
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("stats"))
async def show_stats(message: Message):
    if not message.from_user or not is_admin(message.from_user.id):
        return
        
    users = await get_all_users()
    total_users = len(users)
    total_balance = sum(float(str(user.balance)) for user in users)
    
    await message.answer(
        f"Статистика:\n\n"
        f"Всего пользователей: {total_users}\n"
        f"💰 Общий баланс: {total_balance:.2f} RUB"
    )

class BroadcastStates(StatesGroup):
    waiting_for_message = State()

@router.message(Command("broadcast"), F.from_user.id.in_(ADMIN_IDS))
async def broadcast_command(message: Message, state: FSMContext):
    await message.answer("Отправьте сообщение для рассылки (текст, фото, видео, документ или любой другой контент):")
    await state.set_state(BroadcastStates.waiting_for_message)

@router.message(StateFilter(BroadcastStates.waiting_for_message), F.from_user.id.in_(ADMIN_IDS))
async def process_broadcast_message(message: Message, state: FSMContext):
    if not message.bot:
        return
        
    users = await get_all_users()
    sent = 0
    blocked = 0
    
    await message.answer("Начинаю рассылку...")
    
    for user in users:
        try:
            user_id = int(str(user.user_id))
            if message.text:
                await message.bot.send_message(user_id, message.text)
            elif message.photo:
                await message.bot.send_photo(
                    user_id,
                    message.photo[-1].file_id,
                    caption=message.caption
                )
            elif message.video:
                await message.bot.send_video(
                    user_id,
                    message.video.file_id,
                    caption=message.caption
                )
            elif message.video_note:
                await message.bot.send_video_note(
                    user_id,
                    message.video_note.file_id
                )
            elif message.document:
                await message.bot.send_document(
                    user_id,
                    message.document.file_id,
                    caption=message.caption
                )
            elif message.voice:
                await message.bot.send_voice(
                    user_id,
                    message.voice.file_id,
                    caption=message.caption
                )
            elif message.audio:
                await message.bot.send_audio(
                    user_id,
                    message.audio.file_id,
                    caption=message.caption
                )
            elif message.animation:
                await message.bot.send_animation(
                    user_id,
                    message.animation.file_id,
                    caption=message.caption
                )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            blocked += 1
            logger.error(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")
            continue
            
    await message.answer(
        f"Рассылка завершена!\n"
        f"✅ Успешно отправлено: {sent}\n"
        f"❌ Заблокировали бота: {blocked}"
    )
    await state.clear()

@router.message(Command("add_mod"))
async def add_moderator(message: Message):
    if not message.from_user or not is_admin(message.from_user.id) or not message.text:
        await message.answer("❌ У вас нет доступа к этой команде")
        return
        
    args = message.text.split()
    if len(args) != 3:
        await message.answer(
            "Использование: /add_mod <id> <имя>\n"
            "Пример: /add_mod 123456789 'Модератор #1'"
        )
        return
        
    try:
        mod_id = int(args[1])
        mod_name = args[2]
        
        # Проверяем, не вляется ли пользователь уже модератором
        if mod_id in config.MODERATOR_CHAT_IDS:
            await message.answer("❌ Этот пользователь уже является модератором")
            return
            
        # Добавляем нового модератора
        config.MODERATOR_CHAT_IDS[mod_id] = mod_name
        await message.answer(
            f"✅ Модератор успешно добавлен:\n"
            f"ID: {mod_id}\n"
            f"Имя: {mod_name}"
        )
        
    except ValueError:
        await message.answer("❌ ID должен быть числом")

@router.message(Command("remove_mod"))
async def remove_moderator(message: Message):
    if not message.from_user or not is_admin(message.from_user.id) or not message.text:
        await message.answer("❌ У вас нет доступа к этой команде")
        return
        
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "Использование: /remove_mod <id>\n"
            "Пример: /remove_mod 123456789"
        )
        return
        
    try:
        mod_id = int(args[1])
        
        # Проверяем, является ли пользователь модератором
        if mod_id not in config.MODERATOR_CHAT_IDS:
            await message.answer("❌ Этот пользователь не является модератором")
            return
            
        # Удаляем модератора
        mod_name = config.MODERATOR_CHAT_IDS.pop(mod_id)
        await message.answer(
            f"✅ Модератор успешно удален:\n"
            f"ID: {mod_id}\n"
            f"Имя: {mod_name}"
        )
        
    except ValueError:
        await message.answer("❌ ID должен быть числом")

@router.message(Command("list_mods"))
async def list_moderators(message: Message):
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
        
    if not config.MODERATOR_CHAT_IDS:
        await message.answer("📝 Список модераторов пуст")
        return
        
    mods_list = "\n".join(
        f"• {name} (ID: {mod_id})"
        for mod_id, name in config.MODERATOR_CHAT_IDS.items()
    )
    
    await message.answer(
        f"📝 Список модераторов:\n\n{mods_list}"
    )

@router.message(Command("approve"))
async def approve_payment(message: Message, state: FSMContext):
    if not message.from_user or message.from_user.id != 5349222597 and 881317631 or not message.text or not message.bot:
        return
        
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /approve <user_id> <amount>")
        return
        
    try:
        user_id = int(args[1])
        amount = float(args[2])
        
        # Создаем правильный ключ хранилища
        storage_key = StorageKey(bot_id=message.bot.id, user_id=user_id, chat_id=user_id)
        user_state = FSMContext(storage=state.storage, key=storage_key)
        
        state_data = await user_state.get_data()
        active_promo = state_data.get('active_promo')
        
        if active_promo:
            # Рассчитываем бонус
            if active_promo['is_percentage']:
                bonus = amount * (active_promo['amount'] / 100)
            else:
                bonus = active_promo['amount']
            amount += bonus
            
            # Используем промокод
            await use_promo_code(user_id, active_promo['code'])
            await user_state.update_data(active_promo=None)
        
        # Обновляем баланс пользователя
        if await update_balance(user_id, amount):
            await message.bot.send_message(
                user_id,
                f"✅ Ваш платеж на сумму {amount} RUB подтвержден!\n"
                f"Средства зачислены на баланс."
            )
            await message.answer("✅ Платеж подтвержден")
        else:
            await message.answer("❌ Ошибка при обновлении баланса")
            
    except ValueError:
        await message.answer("❌ Неверный формат данных")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("deny"))
async def deny_payment(message: Message):
    if not message.from_user or message.from_user.id != 5349222597 and 881317631 or not message.text or not message.bot:
        return
        
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /deny <user_id> <amount>")
        return
        
    try:
        user_id = int(args[1])
        amount = float(args[2])
        
        await message.bot.send_message(
            user_id,
            f"❌ Ваш платеж на сумму {amount} RUB отклонен!\n"
            f"Пожалуйста, проверьте правильность оплаты и попробуйте снова."
        )
        await message.answer("✅ Платеж отклонен")
        
    except ValueError:
        await message.answer("❌ Неверный формат данных")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.message(Command("clear_balance"))
async def clear_balance(message: Message):
    if not message.from_user or not is_admin(message.from_user.id) or not message.text:
        await message.answer("❌ У вас нет доступа к этой команде")
        return
        
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "Использование: /clear_balance <user_id>\n"
            "Пример: /clear_balance 123456789"
        )
        return
        
    try:
        user_id = int(args[1])
        
        # Устанавливаем баланс в 0
        if await update_balance(user_id, -await get_user_balance(user_id)):
            await message.answer(
                f"✅ Баланс пользователя {user_id} успешно очищен"
            )
        else:
            await message.answer("❌ Ошибка при очистке баланса")
            
    except ValueError:
        await message.answer("❌ ID должен быть числом")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}") 

@router.message(Command("restart"))
async def restart_command(message: Message):
    if not message.from_user or not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде")
        return
        
    await message.answer("🔄 Бот перезапускается...")
    
    try:
        # Перезапускаем бота
        restart_bot()
    except Exception as e:
        await message.answer(f"❌ Ошибка при перезапуске: {str(e)}") 