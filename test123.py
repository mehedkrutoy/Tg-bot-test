import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.types.web_app_info import WebAppInfo
from aiogram.filters import Command
from aiogram.types import ContentType


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
    markup = types.ReplyKeyboardMarkup(keyboard=[
        [
            types.KeyboardButton(text='Открыть Web Shop', web_app=types.WebAppInfo(url='https://mehedkrutoy.github.io/Tg-bot-test'))
        ]
    ])
    await message.answer('Привет друг!', reply_markup=markup)

@router.message(lambda message: message.web_app_data is not None)
async def web_app(message: types.Message):
    if message.web_app_data:  # Проверяем, что web_app_data не None
        await message.answer(message.web_app_data.data)
    else:
        await message.answer("Нет данных от Web App.")
async def main():
    bot = Bot('7827206500:AAHSUfScTGHCHDLCUphwKW7P7Pm54YZ8Wmo')
    dp = Dispatcher()

    # Регистрируем роутер в диспетчере
    dp.include_router(router)

    # Запускаем polling
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())