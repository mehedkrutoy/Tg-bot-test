from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import aiogram
import config
import sqlite3
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters.state import StateFilter
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import logging
import aiogram.exceptions
import aiomysql
from aiogram.filters.callback_data import CallbackData
import time

# Словарь для хранения времени создания сообщений с кнопками
message_timestamps = {}
# Время жизни кнопок (в секундах)
BUTTON_LIFETIME = 120  # 1 час

алё даун

# Определяем состояния для FSM
class ReplenishStates(StatesGroup):
    waiting_for_amount = State()

class Form(StatesGroup):
    waiting_for_message = State()  # Состояние ожидания сообщения
    in_support_chat = State()  # Состояние активного чата с поддержкой
    waiting_for_promo = State() # Состояние ожидания промокода

class NumberInput(StatesGroup):
    waiting_for_number = State()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

last_bot_message = {}
course_123 = 0.65
group_news = "t.me/channel_news"
group_reviews = "t.me/channel_reviews"

MODERATOR_CHAT_IDS = {
    881317631: "Модератор #228",
    7074139761: "Модератор #1337"
}
API_TOKEN = config.BOT_TOKEN
PAYMENT_TOKEN = config.PAYMENT_TOKEN

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Создаем подключение к базе данных SQLite
def create_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  balance REAL DEFAULT 0,
                  referrer_id INTEGER,
                  total_referrals INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS promo_codes
                 (code TEXT PRIMARY KEY,
                  amount REAL,
                  uses_left INTEGER,
                  is_percentage INTEGER DEFAULT 0)''')  # Добавляем поле is_percentage
    c.execute('''CREATE TABLE IF NOT EXISTS used_promo_codes
                 (user_id INTEGER,
                  code TEXT,
                  PRIMARY KEY (user_id, code))''')
    conn.commit()
    conn.close()

# Функция для получения или создания профиля пользователя
async def get_or_create_user(user_id: int, username = None, referrer_id = None):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    
    if user is None:
        c.execute('INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)',
                 (user_id, username, referrer_id))
        if referrer_id:
            c.execute('UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id = ?',
                     (referrer_id,))
        conn.commit()
        user = (user_id, username, 0, referrer_id, 0)
    
    conn.close()
    return user

# Команда для рассылки сообщения всем пользователям
@router.message(Command("broadcast"))
async def broadcast_command(message: types.Message):
    if message.from_user is None or message.from_user.id not in MODERATOR_CHAT_IDS:
        return
    
    if message.text is None:
        return
    broadcast_text = message.text.replace("/broadcast", "").strip()
    if not broadcast_text:
        await message.answer("Использование: /broadcast <текст сообщения>")
        return
        
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    users = c.fetchall()
    conn.close()
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            await bot.send_message(user[0], broadcast_text)
            success_count += 1
        except Exception as e:
            fail_count += 1
            logging.error(f"Ошибка отправки сообщения пользователю {user[0]}: {e}")
            
    await message.answer(f"Рассылка завершена\nУспешно: {success_count}\nОшибок: {fail_count}")

# Команда для создания промокода (только для модераторов)
@router.message(Command("create_promo"))
async def create_promo_command(message: types.Message):
    if message.from_user is None or message.from_user.id not in MODERATOR_CHAT_IDS:
        return
        
    if message.text is None:
        return
        
    args = message.text.split()
    if len(args) != 5:  # Добавляем новый аргумент для типа промокода
        await message.answer("Использование: /create_promo <код> <сумма/процент> <количество использований> <тип: sum/percent>")
        return
        
    try:
        code = args[1]
        amount = float(args[2])
        uses = int(args[3])
        promo_type = args[4].lower()
        
        if promo_type not in ['sum', 'percent']:
            await message.answer("Тип промокода должен быть 'sum' или 'percent'")
            return
            
        is_percentage = 1 if promo_type == 'percent' else 0
        
        if is_percentage and (amount <= 0 or amount > 100):
            await message.answer("Процент должен быть больше 0 и не более 100")
            return
            
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        # Пересоздаем таблицу с правильной структурой если её нет
        c.execute('''CREATE TABLE IF NOT EXISTS promo_codes
                     (code TEXT PRIMARY KEY,
                      amount REAL,
                      uses_left INTEGER,
                      is_percentage INTEGER DEFAULT 0)''')
                      
        c.execute('INSERT INTO promo_codes (code, amount, uses_left, is_percentage) VALUES (?, ?, ?, ?)',
                 (code, amount, uses, is_percentage))
        conn.commit()
        conn.close()
        
        promo_type_text = "процентный" if is_percentage else "суммовой"
        await message.answer(f"Промокод {code} ({promo_type_text}) создан успешно!")
    except Exception as e:
        await message.answer(f"Ошибка при создании промокода: {str(e)}")

# CallbackData для inline-кнопки
class ButtonCallback(CallbackData, prefix="number"):
    action: str

# Словарь для хранения активных чатов поддержки
support_chats = {}

# Создаем клавиатуру для завершения чата
end_chat_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Завершить чат")]],
    resize_keyboard=True
)

@router.callback_query(F.data == "activate_promo")
async def activate_promo_callback(callback: CallbackQuery, state: FSMContext):
    if callback.message is None:
        return
        
    await state.set_state(Form.waiting_for_promo)
    sent_message = await callback.message.answer("Введите промокод:")
    message_timestamps[sent_message.message_id] = time.time()
    await callback.answer()

@router.message(Form.waiting_for_promo)
async def handle_promo_input(message: types.Message, state: FSMContext):
    if message.from_user is None or message.text is None:
        return
        
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Проверяем существование промокода
    c.execute('SELECT amount, uses_left, is_percentage FROM promo_codes WHERE code = ?', (message.text,))
    promo = c.fetchone()
    
    if not promo:
        await message.answer("Такого промокода не существует!")
        await state.clear()
        conn.close()
        return
        
    # Проверяем, использовал ли пользователь этот промокод
    c.execute('SELECT 1 FROM used_promo_codes WHERE user_id = ? AND code = ?',
             (message.from_user.id, message.text))
    if c.fetchone():
        await message.answer("Вы уже использовали этот промокод!")
        await state.clear()
        conn.close()
        return
        
    amount, uses_left, is_percentage = promo
    if uses_left <= 0:
        await message.answer("Этот промокод больше не действителен!")
        await state.clear()
        conn.close()
        return
        
    # Активируем промокод
    if is_percentage:
        # Если промокод процентный, сохраняем его в состоянии пользователя для использования при пополнении
        await state.update_data(active_promo={"code": message.text, "percent": amount})
        sent_message = await message.answer(f"Промокод активирован! При следующем пополнении вы получите бонус {amount}%")
        
        # Сразу отмечаем промокод как использованный
        c.execute('UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?',
                 (message.text,))
        c.execute('INSERT INTO used_promo_codes (user_id, code) VALUES (?, ?)',
                 (message.from_user.id, message.text))
    else:
        # Если промокод на фиксированную сумму, начисляем её сразу
        c.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?',
                 (amount, message.from_user.id))
        c.execute('UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?',
                 (message.text,))
        c.execute('INSERT INTO used_promo_codes (user_id, code) VALUES (?, ?)',
                 (message.from_user.id, message.text))
        sent_message = await message.answer(f"Промокод активирован! На ваш баланс начислено {amount} RUB")
             
    conn.commit()
    conn.close()
    
    message_timestamps[sent_message.message_id] = time.time()
    await state.clear()

@router.callback_query(F.data == "start_support")
async def support_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user is None or callback.message is None:
        return
        
    # Проверяем время жизни кнопки
    message_id = callback.message.message_id
    if message_id in message_timestamps:
        if time.time() - message_timestamps[message_id] > BUTTON_LIFETIME:
            await callback.answer("Время действия кнопки истекло. Пожалуйста, запросите новое сообщение.", show_alert=True)
            return
            
    user_id = callback.from_user.id
    
    # Проверяем, не является ли отправитель модератором
    if user_id in MODERATOR_CHAT_IDS:
        await callback.message.answer("Вы модератор и не можете создать запрос в поддержку")
        return
        
    # Проверяем, нет ли уже активного чата
    if user_id in support_chats:
        await callback.message.answer("У вас уже есть активный чат с поддержкой")
        return
        
    # Создаем новый чат поддержки
    support_chats[user_id] = {
        "user_id": user_id,
        "username": callback.from_user.username or "Неизвестный пользователь"
    }
    
    # Устанавливаем состояние чата поддержки
    await state.set_state(Form.in_support_chat)
    
    # Отправляем сообщение пользователю с обычной клавиатурой для завершения чата
    sent_message = await callback.message.answer(
        "Чат с поддержкой создан. Отправьте ваше сообщение.\nДля завершения чата нажмите кнопку ниже",
        reply_markup=end_chat_keyboard
    )
    
    # Сохраняем время создания сообщения с кнопкой
    message_timestamps[sent_message.message_id] = time.time()
    
    # Уведомляем модераторов
    for moderator_id in MODERATOR_CHAT_IDS:
        await bot.send_message(
            moderator_id,
            f"Новый запрос в поддержку от пользователя {callback.from_user.username} (ID: {user_id})"
        )
    
    await callback.answer()

# Обработчик сообщений в чате поддержки
@router.message(Form.in_support_chat)
async def handle_support_message(message: types.Message, state: FSMContext):
    if message.from_user is None:
        return
    user_id = message.from_user.id
    
    # Проверяем нажатие кнопки завершения чата
    if message.text == "Завершить чат":
        await end_support_chat(user_id, state)
        await message.answer(
            "Чат с поддержкой завершен",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Главное меню")]],
                resize_keyboard=True
            )
        )
        return
    
    if user_id in MODERATOR_CHAT_IDS:
        # Сообщение от модератора - отправляем пользователю
        try:
            # Проверяем, является ли сообщение ответом
            if not message.reply_to_message:
                await message.answer("Пожалуйста, используйте ответ (reply) на сообщение пользователя")
                return
                
            # Извлекаем ID пользователя из текста сообщения
            text = message.reply_to_message.text
            if not text or "ID:" not in text:
                await message.answer("Не могу найти ID пользователя в сообщении")
                return
                
            # Изменяем способ извлечения ID
            try:
                lines = text.split('\n')
                id_line = next(line for line in lines if 'ID:' in line)
                target_user_id = int(id_line.split('ID:')[1].strip())
            except:
                await message.answer("Ошибка при извлечении ID пользователя")
                return
                
            # Проверяем, существует ли активный чат
            if target_user_id not in support_chats:
                await message.answer("Чат с этим пользователем уже завершен")
                return
                
            # Отправляем ответ пользователю с указанием ID модератора
            moderator_name = MODERATOR_CHAT_IDS[user_id]
            await bot.send_message(target_user_id, f"{moderator_name}: {message.text}")
            await message.answer("✅ Сообщение отправлено пользователю")
            
        except Exception as e:
            await message.answer(f"Ошибка при отправке сообщения: {str(e)}")
            
    else:
        # Сообщение от пользо��ателя - отправляем модераторам
        if user_id in support_chats:
            for moderator_id in MODERATOR_CHAT_IDS:
                await bot.send_message(
                    moderator_id,
                    f"Сообщение от {message.from_user.username or 'Неизвестный'}\nID: {user_id}\n\nТекст: {message.text}"
                )

@router.callback_query(F.data == "end_support")
async def end_support_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user is None or callback.message is None:
        return
        
    # Проверяем время жизни кнопки
    message_id = callback.message.message_id
    if message_id in message_timestamps:
        if time.time() - message_timestamps[message_id] > BUTTON_LIFETIME:
            await callback.answer("Время действия кнопки истекло. Пожалуйста, запросите новое сообщение.", show_alert=True)
            return
            
    user_id = callback.from_user.id
    await end_support_chat(user_id, state)
    await callback.message.answer(
        "Чат с поддержкой завершен",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Главное меню")]],
            resize_keyboard=True
        )
    )
    await callback.answer()

async def end_support_chat(user_id: int, state: FSMContext):
    if user_id in support_chats:
        del support_chats[user_id]
    await state.clear()

# Inline кнопки для стартового меню
start_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Пополнить", callback_data="replenish"),
        InlineKeyboardButton(text="Вывод", callback_data="withdraw")
    ],
    [
        InlineKeyboardButton(text="Профиль", callback_data="profile"),
        InlineKeyboardButton(text="Курс", callback_data="course")
    ],
    [
        InlineKeyboardButton(text="Новостник", callback_data="news"),
        InlineKeyboardButton(text="Отзывы", callback_data="reviews"),
        InlineKeyboardButton(text="Поддержка", callback_data="support")
    ],
    [
        InlineKeyboardButton(text="Калькулятор", callback_data="calculator")
    ]
])

# Кнопка "Главное меню"
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Главное меню")]
    ],
    resize_keyboard=True
)

# ��ендлер команды /start
@router.message(Command("start"))
async def start_command_handler(message: types.Message):
    if message.from_user is None or message.text is None:
        return
        
    # Создаем базу данных если её нет
    create_db()
    
    # Проверяем наличие реферального коа
    args = message.text.split()
    referrer_id = None
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
        except ValueError:
            pass
            
    # Получаем или создаем профиль пользователя
    await get_or_create_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        referrer_id=referrer_id
    )
    
    # Удаляем предыдущее сообщение бота (если есть)
    if message.chat.id in last_bot_message:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=last_bot_message[message.chat.id])
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")
    
    # Отправляем новое сообщение
    sent_message = await message.answer(
        "Добро пожаловать! Выберите действие:",
        reply_markup=start_keyboard
    )

    # Сохраняем ID нового сообщения и время его создания
    last_bot_message[message.chat.id] = sent_message.message_id
    message_timestamps[sent_message.message_id] = time.time()

# Хендлер кнопки "Главное меню"
@router.message(F.text == "Главное меню")
async def main_menu_handler(message: types.Message):
    sent_message = await message.answer(
        "Добро пожаловать! Выберите действие:",
        reply_markup=start_keyboard
    )
    message_timestamps[sent_message.message_id] = time.time()

# calculator
# Обработка нажатия кнопки
@router.callback_query(F.data == "calculator")
async def handle_calculator_button(callback: CallbackQuery, state: FSMContext):
    logging.info("Нажата кнопка 'Калькулятор'")
    if callback.message is None:
        logging.error("Сообщение callback отсутствует.")
        return
        
    # Проверяем время жизни кнопки
    message_id = callback.message.message_id
    if message_id in message_timestamps:
        if time.time() - message_timestamps[message_id] > BUTTON_LIFETIME:
            await callback.answer("Время действи�� кнопки истекло. Пожалуйста, запросите новое сообщение.", show_alert=True)
            return

    try:
        # Удаляем предыдущее сообщение, если оно существует
        if callback.message.chat.id in last_bot_message:
            try:
                await bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=last_bot_message[callback.message.chat.id]
                )
                del last_bot_message[callback.message.chat.id]
            except aiogram.exceptions.TelegramBadRequest as e:
                if "message to delete not found" in str(e):
                    logging.warning("Сообщение уже удалено. Удаляем запись из last_bot_message.")
                    del last_bot_message[callback.message.chat.id]
                else:
                    logging.error(f"Ошибка удаления сообщения: {e}")
            except Exception as e:
                logging.error(f"Непредвиденная ошибка при удалении сообщения: {e}")

        # Отправляем новое сообщение
        sent_message = await callback.message.answer("Введите число для умножения:")
        logging.info(f"Новое сообщение отправлено: {sent_message.message_id}")
        last_bot_message[callback.message.chat.id] = sent_message.message_id
        message_timestamps[sent_message.message_id] = time.time()

        # Устанавливаем состояние FSM
        await state.set_state(NumberInput.waiting_for_number)
        current_state = await state.get_state()
        logging.info(f"Состояние FSM после установки: {current_state}")

    except Exception as e:
        logging.error(f"Ошибка в обработке кнопки 'Калькулятор': {e}")

    await callback.answer()

@router.message(NumberInput.waiting_for_number)
async def handle_number_input(message: types.Message, state: FSMContext):
    try:
        if message.text is None:
            return
        value = float(message.text.replace(",", "."))  # Обработка числа с запятой
        result = course_123 * value
        sent_message = await message.answer(
            f"Результат: {result}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")]
                ]
            )
        )
        message_timestamps[sent_message.message_id] = time.time()
        logging.info(f"Результат вычисения: {result}")
        await state.clear()
    except ValueError:
        logging.error(f"Некорректный ввод: {message.text}")
        await message.answer("Пожалуйста, введите корректное число.")
@router.callback_query()
async def inline_button_handler(callback: CallbackQuery, state: FSMContext):
    if callback.data == "calculator":
        logging.debug("Кнопка 'Калькулятор' обрабатывается отдельным хендлером.")
        return  # Пропускаем обработку

    if callback.from_user is None or not callback.message:
        return
        
    # Проверяем время жизни кнопки
    message_id = callback.message.message_id
    if message_id in message_timestamps:
        if time.time() - message_timestamps[message_id] > BUTTON_LIFETIME:
            await callback.answer("Время действия кнопки истекло. Пожалуйста, запросите новое сообщение.", show_alert=True)
            return

    # Получаем данные пользователя из БД для профиля
    if callback.data == "profile":
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT balance, total_referrals FROM users WHERE user_id = ?', (callback.from_user.id,))
        user_data = c.fetchone()
        conn.close()

        if user_data:
            balance, total_referrals = user_data
            ref_link = f"https://t.me/{(await bot.me()).username}?start={callback.from_user.id}"
            profile_text = f"""👤 Ваш профиль:
            
💰 Баланс: {balance} RUB
👥 Рефералов: {total_referrals}

🔗 Ваш рефральная ссылка:
{ref_link}

💎 За каждого приглашенного пользователя вы получаете 5% от его пополнений!"""
            
            if user_data and callback.message:
                try:
                    # Удаляем предыдущее сообщение
                    if callback.message.chat.id in last_bot_message:
                        try:
                            await bot.delete_message(
                                chat_id=callback.message.chat.id,
                                message_id=last_bot_message[callback.message.chat.id]
                            )
                        except Exception as e:
                            logging.error(f"Ошибка при удалени�� сообщения: {e}")
                            
                    sent_message = await bot.send_message(
                        chat_id=callback.message.chat.id,
                        text=profile_text,
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="Активировать промокод", callback_data="activate_promo")],
                            [InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")]
                        ])
                    )
                    last_bot_message[callback.message.chat.id] = sent_message.message_id
                    message_timestamps[sent_message.message_id] = time.time()
                except Exception as e:
                    logging.error(f"Ошибка при обновлении профиля: {e}")
                    
            await callback.answer()
            return

    actions = {
        "replenish": {
            "text": "🖋 Выберите способ оплаты ⤵️",
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Оплата картой", callback_data="card_payment")
                ],
                [
                    InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")
                ]
            ])
        },

        "support": {
            "text": f"""🧑‍💻 Часто задаваемые вопросы:

1. Почему так долго проверяют чек?
• Чеки проверяются в ручную, а не автоматически. Сотрудники не согут поверить чек, если вы пополнили в познее время или раннее вечером. До 24 часов занимает проверка чека.

2. Почему так долго выводят золото?
• Вывод золота занимает до 24 часов. Но мы стараемся как можно быстрее вывести вам золото. Возможно сотрудник взял перерыв или ваш скин трудно найти

3. Сколько по времени выводят золото?
• Вывод золота происходит до 24 часов от запроса на вывод. Но в большинстве вывод происходит от нескольких минут до чаа.

4. Безопасно ли у вас покупать?
• Весь товар, который продётся в боте, получен честным путём. Если вы сомневаетесь  безопасности, то лучше покупать в игре.

💡 Прежде чем задать вопрос, убедитесь что здесь нету ответа на ваш вопрос

Связаться - @pr1nce82. При возникновении проблем, вы можете написать в поддержку""",
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Связаться с поддержкой", callback_data="start_support")
                ],
                [
                    InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")
                ]
            ])
        },

        "reviews": {
            "text": f"""✅ Наши отзывы - {group_reviews}
🏹 Если у вас есть какие-либо сомнения при покупке голды, то вы можете посмотреть отзывы и убедиться в нашей честности.""",
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Отзывы", url=group_reviews)
                ],
                [
                    InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")
                ]
            ])
        },

        "news": {
            "text": f"""📰 На новостник - {group_news}⚠️
Публиуем исключительно важные новости по боту и Standoff2""",
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Перейти в новостник", url=group_news)
                ],
                [
                    InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")
                ]
            ])
        },

        "course": {
            "text": f'Курс: {course_123}',
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")
                ]
            ])
        },

        "withdraw": {
            "text": "Вы выбрали вывод. Что вы хотите сделать дальше?",
            "keyboard": InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Вывести на карту", callback_data="withdraw_card"),
                    InlineKeyboardButton(text="История выводов", callback_data="withdraw_history")
                ],
                [
                    InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")
                ]
            ])
        },

        "main_menu": {
            "text": "Добро пожаловать! Выберите действие:",
            "keyboard": start_keyboard
        },
    }

    if not callback.message or not callback.message.chat:
        await callback.answer("Ошибка: Сообщение недоступно.", show_alert=True)
        return

    chat_id = callback.message.chat.id

    # Удаляем предыдущее сообщение бота
    if chat_id in last_bot_message:
        try:
            await bot.delete_message(
                chat_id=chat_id,
                message_id=last_bot_message[chat_id]
            )
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение: {e}")

    # Обработка платежа картой
    if callback.data == "card_payment":
        await bot.send_invoice(
            chat_id=chat_id,
            title="Пополнение баланса",
            description="Пополнение баланса через платежную систему",
            payload="payment_balance",
            provider_token=PAYMENT_TOKEN,
            currency="RUB",
            prices=[
                LabeledPrice(label="Пополнение", amount=5000)  # 50 рублей (в копейках)
            ]
        )
        return

    # Отправляем новое сообщение
    if callback.data in actions:
        action = actions[callback.data]
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=action["text"],
            reply_markup=action["keyboard"]
        )
        last_bot_message[chat_id] = sent_message.message_id
        message_timestamps[sent_message.message_id] = time.time()
    else:
        await callback.answer("Неизвестное действие", show_alert=True)

    await callback.answer()

# Обработчик pre_checkout_query
@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Обработчик успешного платежа
# Обработчик успешного платежа
@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message, state: FSMContext):
    if message.successful_payment is None or message.from_user is None:
        return
    
    payment_amount = message.successful_payment.total_amount / 100
    bonus_amount = 0
    
    state_data = await state.get_data()
    active_promo = state_data.get('active_promo')
    
    if active_promo:
        bonus_percent = active_promo['percent']
        bonus_amount = payment_amount * (bonus_percent / 100)
        payment_amount += bonus_amount

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    try:
        # Обновляем баланс пользователя
        c.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?',
                 (payment_amount, message.from_user.id))

        # Применяем промокод только после успешного обновления баланса
        if active_promo:
            c.execute('UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?', 
                     (active_promo['code'],))
            c.execute('INSERT INTO used_promo_codes (user_id, code) VALUES (?, ?)',
                     (message.from_user.id, active_promo['code']))
        
        conn.commit()
        await state.clear()  # Очищаем состояние только после коммита
        
        success_message = f"Платеж на сумму {payment_amount} RUB успешно выполнен!"
        if active_promo:
            success_message += f"\nБонус по промокоду: {bonus_amount} RUB"
        
        await message.answer(success_message)
    
    except Exception as e:
        logging.error(f"Ошибка при обработке платежа: {e}")
        await message.answer("Произошла ошибка при обработке платежа.")
        conn.rollback()
    
    finally:
        conn.close()


@router.message()
async def handle_moderator_message(message: types.Message):
    if message.from_user is None or message.text is None:
        return
    
    if message.from_user.id in MODERATOR_CHAT_IDS:
        try:
            # Проверяем, является ли сообщение ответом
            if not message.reply_to_message:
                await message.answer("Пожалуйста, используйте ответ (reply) на сообщение пользователя")
                return
                
            # Извлекаем ID пользователя из текста сообщени��
            text = message.reply_to_message.text
            if not text or "ID:" not in text:
                await message.answer("Не могу найти ID пользователя в сообщении")
                return
                
            try:
                lines = text.split('\n')
                id_line = next(line for line in lines if 'ID:' in line)
                target_user_id = int(id_line.split('ID:')[1].strip())
            except:
                await message.answer("Ошибка при извлечении ID пользователя")
                return
                
            # Проверяем, существует ли активный чат
            if target_user_id not in support_chats:
                await message.answer("Чат с этим пользователем уже завершен")
                return
                
            # Отправляем ответ пользователю с указанием ID модератора
            moderator_name = MODERATOR_CHAT_IDS[message.from_user.id]
            await bot.send_message(target_user_id, f"{moderator_name}: {message.text}")
            await message.answer("✅ Сообщение отправлено пользователю")
            
        except Exception as e:
            await message.answer(f"Ошибка при отправке сообщения: {str(e)}")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))