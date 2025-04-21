# bot.py

# Import necessary libraries
from dotenv import load_dotenv
import os
import logging
import json_log_formatter
from database import create_table
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.utils.token import TokenValidationError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from handlers import register_handlers
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.methods.set_chat_menu_button import SetChatMenuButton
from aiogram.types import MenuButtonDefault

def setup_logging():
    # Set up JSON logging
    formatter = json_log_formatter.JSONFormatter()
    json_handler = logging.StreamHandler()
    json_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(json_handler)
    logger.setLevel(logging.INFO)
    return logger

def on_startup():
    # Log the start of the bot
    logger.info('Bot is starting')
    # Ensure the prayers table is created
    create_table()
    # Register all handlers

async def main():
    # Load environment variables from .env file
    load_dotenv()

    # Get the token from the environment
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable is not set!")

    # Initialize the bot and storage
    storage = MemoryStorage()
    bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    # Initialize the dispatcher with storage (v3 way)
    dp = Dispatcher(storage=storage)
    
    # Register all handlers
    register_handlers(dp)
    
    # No more middleware.setup, use dp.update.middleware instead if needed
    
    # Set up commands for the bot
    commands = [
        BotCommand(command="start", description="Розпочати роботу з ботом"),
        BotCommand(command="send_prayer", description="Надіслати молитву"),
        BotCommand(command="my_prayers", description="Показати мої молитви"),
        BotCommand(command="all_prayers", description="Показати всі молитви")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    
    # Set menu button to default type (hamburger menu)
    await bot.set_chat_menu_button(
        menu_button=MenuButtonDefault()
    )
    
    # Start polling updates instead of using executor
    logger.info('Starting bot')
    
    # To skip pending updates if needed:
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Start polling (v3 way)
    await dp.start_polling(bot, skip_updates=False)

if __name__ == '__main__':
    # Setup logging
    logger = setup_logging()
    # Run the bot
    import asyncio
    on_startup()
    asyncio.run(main()) 