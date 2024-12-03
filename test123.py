import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types.web_app_info import WebAppInfo
from aiogram.filters import Command


#скип ошибок
from pydantic import BaseModel, ValidationError
class Model(BaseModel):
    x: str
try:
    Model(x="")
except ValidationError as exc:
    print(repr(exc.errors()[0]['type']))
    #> 'missing'


router = Router()

@router.message(Command(commands=["start"]))
async def start(message: types.Message):
    markup = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text='Открыть Web Shop', web_app=types.WebAppInfo(url='https://mehedkrutoy.github.io/Tg-bot-test'))
        ]
    ])

    # markup = types.InlineKeyboardMarkup(inline_keyboard=[
    #     [
    #         types.InlineKeyboardButton(
    #             text='Открыть Web Shop',
    #             web_app=types.WebAppInfo(url='https://mehedkrutoy.github.io/Tg-bot-test')
    #         )
    #     ]
    # ])
    await message.answer('Привет друг!', reply_markup=markup)


async def main():
    bot = Bot('7827206500:AAHSUfScTGHCHDLCUphwKW7P7Pm54YZ8Wmo')
    dp = Dispatcher()

    # Регистрируем роутер в диспетчере
    dp.include_router(router)

    # Запускаем polling
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())