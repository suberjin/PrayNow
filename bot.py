# bot.py

# Import necessary libraries
from dotenv import load_dotenv
import os
import logging
import json_log_formatter
from database import create_table
from aiogram import Bot, Dispatcher
from aiogram.types import ParseMode
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from handlers import register_handlers

def setup_logging():
    # Set up JSON logging
    formatter = json_log_formatter.JSONFormatter()
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(json_handler)
    logger.setLevel(logging.INFO)
    return logger

async def on_startup(dp: Dispatcher):
    # Log the start of the bot
    logger.info('Bot is starting')
    # Ensure the prayers table is created
    create_table()
    # Register all handlers
    register_handlers(dp)

def main():
    # Load environment variables from .env file
    load_dotenv()

    # Get the token from the environment
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable is not set!")

    # Initialize the bot and dispatcher with MemoryStorage
    storage = MemoryStorage()
    bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(bot, storage=storage)
    dp.middleware.setup(LoggingMiddleware())

    # Start the bot using aiogram's executor
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup
    )

if __name__ == '__main__':
    # Setup logging
    logger = setup_logging()
    # Run the bot
    main() 