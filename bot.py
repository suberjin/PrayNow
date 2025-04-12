# bot.py

# Import necessary libraries
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
from dotenv import load_dotenv
import os
import logging
import json_log_formatter
import sqlite3
from datetime import datetime
from database import create_table
from services import insert_prayer, fetch_prayers, update_prayer, delete_prayer
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Load environment variables from .env file
load_dotenv()

# Get the token from the environment
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Set up JSON logging
formatter = json_log_formatter.JSONFormatter()
json_handler = logging.StreamHandler()
json_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(json_handler)
logger.setLevel(logging.INFO)

# Log the start of the bot
logger.info('Bot is starting')

# Ensure the prayers table is created
create_table()

# Define the PrayerStates class
class PrayerStates(StatesGroup):
    expecting_prayer = State()

# Initialize the bot and dispatcher with MemoryStorage
storage = MemoryStorage()
bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Define a simple start command handler
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('send pray', callback_data='send_pray'))
    keyboard.add(types.InlineKeyboardButton('Show my prayers', callback_data='show_my_prayers'))
    await message.reply("Hello! I am your bot.", reply_markup=keyboard)

# Define a callback query handler
@dp.callback_query_handler(lambda c: c.data == 'send_pray')
async def process_callback_send_pray(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, "Please enter your prayer:")
    await PrayerStates.expecting_prayer.set()
    logger.info('State set to expecting_prayer')

# Define a message handler to capture user input
@dp.message_handler(state=PrayerStates.expecting_prayer)
async def capture_prayer(message: types.Message, state: FSMContext):
    logger.info('Received prayer: %s', message.text)
    # Insert prayer into the database
    # Reset state
    await message.reply("Prayer recorded.")
    await state.finish()

# Define a command handler to list prayers
def my_prayers(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    logger.info('Fetching prayers for user_id: %s', user_id)
    prayers = fetch_prayers(user_id)
    message = update.message if update.message else update.callback_query.message
    if not prayers:
        message.reply_text('You have no prayers recorded.')
        return

    for prayer_id, prayer_text in prayers:
        keyboard = [
            [InlineKeyboardButton('Edit', callback_data=f'edit_{prayer_id}'),
             InlineKeyboardButton('Delete', callback_data=f'delete_{prayer_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message.reply_text(prayer_text, reply_markup=reply_markup)

# Define a callback query handler for editing and deleting prayers
def prayer_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    data = query.data

    if data == 'main_menu':
        # Log returning to the main menu
        logger.info('Returning to main menu')

        # Reset user-specific states
        context.user_data.clear()

        # Delete the previous message to avoid confusion
        query.message.delete()

        # Send a new message to return to the main menu
        context.bot.send_message(chat_id=query.message.chat_id, text='Hello! I am your bot.', reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('send pray', callback_data='send_pray')],
            [InlineKeyboardButton('Show my prayers', callback_data='show_my_prayers')]
        ]))
    elif data == 'show_my_prayers':
        # Call the my_prayers function
        logger.info('Fetching prayers for user_id')
        my_prayers(update, context)
    elif data.startswith('edit_'):
        prayer_id = int(data.split('_')[1])
        query.edit_message_text(text='Please enter the new prayer text:')
        context.user_data['edit_prayer_id'] = prayer_id
        context.user_data['expecting_edit'] = True

    elif data.startswith('delete_'):
        prayer_id = int(data.split('_')[1])
        delete_prayer(prayer_id)
        query.edit_message_text(text='Prayer deleted.')

# Define a message handler to capture edited prayer text
def capture_edit(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('expecting_edit'):
        prayer_id = context.user_data['edit_prayer_id']
        new_text = update.message.text
        update_prayer(prayer_id, new_text)
        update.message.reply_text('Prayer updated.')
        context.user_data['expecting_edit'] = False

# Define a callback query handler for showing prayers
@dp.callback_query_handler(lambda c: c.data == 'show_my_prayers')
async def show_my_prayers(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info('Fetching prayers for user_id: %s', user_id)
    prayers = fetch_prayers(user_id)
    
    if not prayers:
        await bot.send_message(callback_query.from_user.id, 'You have no prayers recorded.')
        return

    for prayer_id, prayer_text in prayers:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton('Edit', callback_data=f'edit_{prayer_id}'))
        keyboard.add(types.InlineKeyboardButton('Delete', callback_data=f'delete_{prayer_id}'))
        await bot.send_message(callback_query.from_user.id, prayer_text, reply_markup=keyboard)

    await bot.answer_callback_query(callback_query.id)

# Main function to start the bot
def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Register the start command handler
    dp.add_handler(CommandHandler('start', start))

    # Register the callback query handler
    dp.add_handler(CallbackQueryHandler(process_callback_send_pray, pattern='^send_pray$'))

    # Register the message handler
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, capture_prayer))

    # Register the command handler to list prayers
    dp.add_handler(CommandHandler('my_prayers', my_prayers))

    # Register the callback query handler for editing and deleting prayers
    dp.add_handler(CallbackQueryHandler(prayer_callback, pattern='^(main_menu|edit_\\d+|delete_\\d+|show_my_prayers)$'))

    # Register the message handler to capture edited prayer text
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, capture_edit))

    # Register the callback query handler for showing prayers
    dp.register_callback_query_handler(show_my_prayers, lambda c: c.data == 'show_my_prayers')

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()

    # Log when the bot is running
    logger.info('Bot is running')

    # Log when the bot is stopped
    logger.info('Bot has stopped')

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True) 