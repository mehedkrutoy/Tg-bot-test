import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
from config.config import config
from handlers import register_all_handlers
from database.methods import create_db
import signal
import sys
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    logger.info("Received signal to restart...")
    sys.exit(0)

async def main():
    # Регистрируем обработчик сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Создание базы данных
    create_db()

    # Регистрация всех обработчиков
    register_all_handlers(dp)
 
    # Запуск бота
    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Critical error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")

