from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from keyboards.reply import get_main_menu_keyboard


def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
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
        ],


    ])
    # await state.clear(
    #     reply_markup=get_start_keyboard()
    #     )
    # return


def get_payment_methods_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Сбербанк", callback_data="pay_sber"),
            InlineKeyboardButton(text="Тинькофф", callback_data="pay_tinkoff")
        ],
        [
            InlineKeyboardButton(text="OZON", callback_data="pay_ozon")
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")
        ]
    ])

def get_profile_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Активировать промокод", callback_data="activate_promo")
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")
        ]
    ])

def get_support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Связаться с поддержкой", callback_data="start_support")
        ],
        [
            InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")
        ]
    ])
    

def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
    )

# def get_main_menu_reply_keyboard() -> ReplyKeyboardMarkup:
#     return ReplyKeyboardMarkup(
#         keyboard=[
#             [KeyboardButton(text="🔙 Главное меню")]
#         ],
#         resize_keyboard=True,
#         one_time_keyboard=False
#     )