# bot.py

# Import necessary libraries
from dotenv import load_dotenv
import os
import logging
import json_log_formatter
import asyncio
from database import create_table
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog.setup import setup_dialogs
from handlers import register_handlers
from dialogs import dialog
from aiogram.enums import ParseMode

def setup_logging():
    # Set up JSON logging
    formatter = json_log_formatter.JSONFormatter()
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(json_handler)
    logger.setLevel(logging.INFO)
    return logger

async def on_startup(dp: Dispatcher, bot: Bot):
    # Log the start of the bot
    logger.info('Bot is starting')
    # Ensure the prayers table is created
    create_table()
    # Register all handlers
    register_handlers(dp)

async def main():
    # Load environment variables from .env file
    load_dotenv()

    # Get the token from the environment
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable is not set!")

    # Initialize the bot and dispatcher with MemoryStorage
    storage = MemoryStorage()
    bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=storage)
    
    # Setup logging
    logger.info('Setting up bot with logging')

    # Setup dialogs
    setup_dialogs(dp)

    # Register dialog
    dp.include_router(dialog)

    # Call startup handler
    await on_startup(dp, bot)
    
    # Start polling
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    # Setup logging
    logger = setup_logging()
    # Run the bot
    asyncio.run(main()) 