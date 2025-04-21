# bot.py

# Import necessary libraries
from dotenv import load_dotenv
import os
import logging
import json_log_formatter
from database import create_table, is_user_whitelisted
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.utils.token import TokenValidationError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from handlers import register_handlers
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from aiogram.methods.set_chat_menu_button import SetChatMenuButton
from aiogram.types import MenuButtonDefault
from aiogram.filters import Filter
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable, Union
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.event.bases import CancelHandler

# Admin user ID
ADMIN_USER_ID = 282269567

# Custom filter for admin commands
class AdminFilter(Filter):
    async def __call__(self, message: Message) -> bool:
        try:
            user_id = message.from_user.id
            is_admin = user_id == ADMIN_USER_ID
            
            if not is_admin:
                logger.warning(f"Non-admin user {user_id} attempted to use admin command: {message.text}")
            
            return is_admin
        except Exception as e:
            logger.error(f"Error in AdminFilter: {str(e)}")
            return False

# Middleware for whitelist check
class WhitelistMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        # Get user info
        user = event.from_user
        user_id = user.id
        username = user.username
        
        # Always allow admin
        if user_id == ADMIN_USER_ID:
            return await handler(event, data)
        
        # Check if user is in whitelist
        if not is_user_whitelisted(user_id, username):
            logger.info(f"Access denied for user {user_id} ({username}): not in whitelist")
            
            try:
                # Friendly message that access is not yet available
                friendly_message = (
                    "🙏 Вітаю! Цей бот наразі доступний лише для обмеженого кола користувачів. "
                    "Якщо ви хочете отримати доступ, будь ласка, зв'яжіться з @suberjin. "
                    "Дякуємо за розуміння!"
                )
                
                # Send message that access is denied
                if isinstance(event, Message):
                    await event.answer(friendly_message)
                elif isinstance(event, CallbackQuery):
                    await event.message.answer(friendly_message)
                    await event.answer()
            except Exception as e:
                logger.error(f"Error sending access denied message: {str(e)}")
            
            # Return None instead of raising CancelHandler
            return None
        
        # If user is whitelisted, proceed to the handler
        return await handler(event, data)

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
    register_handlers(dp, AdminFilter())
    
    # Add whitelist middleware
    dp.message.middleware(WhitelistMiddleware())
    dp.callback_query.middleware(WhitelistMiddleware())
    
    # Set up commands for all users
    commands = [
        BotCommand(command="start", description="Розпочати роботу з ботом"),
        BotCommand(command="send_prayer", description="Надіслати молитву"),
        BotCommand(command="my_prayers", description="Показати мої молитви"),
        BotCommand(command="all_prayers", description="Показати всі молитви")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    
    # Set up admin commands (only visible to admin)
    admin_commands = commands + [
        BotCommand(command="whitelist_add", description="Додати користувача до білого списку"),
        BotCommand(command="whitelist_remove", description="Видалити користувача з білого списку"),
        BotCommand(command="whitelist_list", description="Показати список дозволених користувачів")
    ]
    
    try:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=ADMIN_USER_ID))
        logger.info(f"Admin commands set for user {ADMIN_USER_ID}")
    except Exception as e:
        logger.error(f"Failed to set admin commands: {str(e)}. Admin may need to interact with the bot first.")
    
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