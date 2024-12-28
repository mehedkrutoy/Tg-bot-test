from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Главное меню")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_end_chat_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Завершить чат")]
        ],
        resize_keyboard=True
    )

def get_support_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Связаться с поддержкой")],
            [KeyboardButton(text="Главное меню")]
        ],
        resize_keyboard=True
    ) 