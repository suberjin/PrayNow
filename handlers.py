from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
import logging
from services import insert_prayer, fetch_prayers, update_prayer, delete_prayer, get_prayer_by_id
from dialogs import dialog, PrayerDialog
from aiogram_dialog import DialogManager, StartMode

# Get logger
logger = logging.getLogger(__name__)

# Define the PrayerStates class
class PrayerStates(StatesGroup):
    expecting_prayer = State()

async def start_handler(message: types.Message, dialog_manager: DialogManager):
    await dialog_manager.start(PrayerDialog.MAIN, mode=StartMode.RESET_STACK)

async def process_callback_send_pray(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await callback_query.answer(show_alert=False)
    await callback_query.message.answer("Please enter your prayer:")
    await state.set_state(PrayerStates.expecting_prayer)
    logger.info('State set to expecting_prayer')

async def capture_prayer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or 'unknown'
    prayer_text = message.text

    # Check if we're editing an existing prayer
    state_data = await state.get_data()
    if 'edit_prayer_id' in state_data:
        prayer_id = state_data['edit_prayer_id']
        update_prayer(prayer_id, prayer_text)
        await message.answer("Prayer updated.")
    else:
        insert_prayer(user_id, username, prayer_text)
        await message.answer("Prayer recorded.")

    await state.clear()

async def my_prayers(message: types.Message):
    user_id = message.from_user.id
    logger.info('Fetching prayers for user_id: %s', user_id)
    prayers = fetch_prayers(user_id)
    
    if not prayers:
        await message.answer('You have no prayers recorded.')
        return

    for prayer_id, prayer_text in prayers:
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text='Edit', callback_data=f'edit_{prayer_id}'),
                    types.InlineKeyboardButton(text='Delete', callback_data=f'delete_{prayer_id}')
                ]
            ]
        )
        await message.answer(prayer_text, reply_markup=keyboard)

async def prayer_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer(show_alert=False)
    data = callback_query.data

    if data.startswith('edit_'):
        prayer_id = int(data.split('_')[1])
        original_text = get_prayer_by_id(prayer_id)
        if original_text:
            await callback_query.message.answer(text=f'Please edit your prayer:\n\n{original_text}')
            await state.update_data(edit_prayer_id=prayer_id)
            await state.set_state(PrayerStates.expecting_prayer)
        else:
            await callback_query.message.answer(text='Sorry, prayer not found.')

    elif data.startswith('delete_'):
        prayer_id = int(data.split('_')[1])
        delete_prayer(prayer_id)
        await callback_query.message.answer(text='Prayer deleted.')

async def show_my_prayers(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info('Fetching prayers for user_id: %s', user_id)
    prayers = fetch_prayers(user_id)
    
    if not prayers:
        await callback_query.message.answer('You have no prayers recorded.')
        return

    for prayer_id, prayer_text in prayers:
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text='Edit', callback_data=f'edit_{prayer_id}'),
                    types.InlineKeyboardButton(text='Delete', callback_data=f'delete_{prayer_id}')
                ]
            ]
        )
        await callback_query.message.answer(prayer_text, reply_markup=keyboard)

    await callback_query.answer(show_alert=False)

def register_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command("start"))
    dp.callback_query.register(process_callback_send_pray, lambda c: c.data == 'send_pray')
    dp.callback_query.register(prayer_callback, lambda c: c.data.startswith(('edit_', 'delete_')))
    dp.callback_query.register(show_my_prayers, lambda c: c.data == 'show_my_prayers')
    dp.message.register(capture_prayer, PrayerStates.expecting_prayer)
