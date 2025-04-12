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

# Define a simple start command handler
def start(update: Update, context: CallbackContext) -> None:
    # Determine if the call is from a message or a callback query
    if update.message:
        # Called from a message
        message = update.message
    else:
        # Called from a callback query
        message = update.callback_query.message

    # Create an inline keyboard with a single button
    keyboard = [[InlineKeyboardButton('send pray', callback_data='send_pray')],
                [InlineKeyboardButton('Show my prayers', callback_data='show_my_prayers')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send a message with the inline keyboard
    message.reply_text('Hello! I am your bot.', reply_markup=reply_markup)

    # Log the incoming request
    logger.info('Received /start command', extra={
        'user_id': update.effective_user.id,
        'username': update.effective_user.username,
        'user_message': message.text if update.message else 'callback'
    })

# Define a callback query handler
def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Please enter your prayer:")

    # Set the state to expect a message
    context.user_data['expecting_prayer'] = True

# Define a message handler to capture user input
def capture_prayer(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('expecting_prayer'):
        # Log the user's prayer
        logger.info('User prayer received', extra={
            'user_id': update.effective_user.id,
            'username': update.effective_user.username,
            'prayer': update.message.text
        })
        
        # Insert the prayer into the database
        insert_prayer(update.effective_user.id, update.effective_user.username, update.message.text)
        
        # Add a button to return to the main menu
        keyboard = [[InlineKeyboardButton('К главному окну', callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Prayer recorded.', reply_markup=reply_markup)
        
        # # Reset the state
        # context.user_data['expecting_prayer'] = False

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

# Main function to start the bot
def main() -> None:
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Register the start command handler
    dp.add_handler(CommandHandler('start', start))

    # Register the callback query handler
    dp.add_handler(CallbackQueryHandler(button_callback, pattern='^send_pray$'))

    # Register the message handler
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, capture_prayer))

    # Register the command handler to list prayers
    dp.add_handler(CommandHandler('my_prayers', my_prayers))

    # Register the callback query handler for editing and deleting prayers
    dp.add_handler(CallbackQueryHandler(prayer_callback, pattern='^(main_menu|edit_\\d+|delete_\\d+|show_my_prayers)$'))

    # Register the message handler to capture edited prayer text
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, capture_edit))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()

    # Log when the bot is running
    logger.info('Bot is running')

    # Log when the bot is stopped
    logger.info('Bot has stopped')

if __name__ == '__main__':
    main() 