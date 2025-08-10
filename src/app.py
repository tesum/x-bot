import asyncio
import logging
import coloredlogs
from aiogram import Bot, Dispatcher
from config import config
from database import init_db
from handlers import setup_handlers

# Настройка логирования
coloredlogs.install(level='DEBUG')
logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    await init_db()
    logger.info("Database initialized")
    
    setup_handlers(dp)
    logger.info("Handlers registered")
    
    logger.info("Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())