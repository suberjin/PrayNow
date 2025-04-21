from aiogram import Bot, Router, F, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
from services import (
    insert_prayer, fetch_prayers, update_prayer, delete_prayer, get_prayer_by_id, 
    fetch_all_prayers, count_all_prayers, fetch_prayers_by_category, 
    fetch_all_prayers_by_category, count_prayers_by_category
)
from database import get_all_categories, get_category_by_id, cursor
from datetime import datetime

# Get logger
logger = logging.getLogger(__name__)

# Create router instance
router = Router()

# Define the PrayerStates class
class PrayerStates(StatesGroup):
    selecting_category = State()
    expecting_prayer = State()
    
    @classmethod
    def get_state_names(cls):
        """Helper function to log all state names for debugging"""
        return {
            cls.selecting_category: "selecting_category",
            cls.expecting_prayer: "expecting_prayer"
        }

# Функция для создания главного меню
async def show_main_menu(message_or_callback):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Надіслати молитву', callback_data='send_pray')],
        [InlineKeyboardButton(text='Показати всі молитви', callback_data='show_all_prayers')],
        [InlineKeyboardButton(text='Показати мої молитви', callback_data='show_my_prayers')],
    ])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer("Головне меню:", reply_markup=keyboard)
    else:  # CallbackQuery
        await message_or_callback.message.answer("Головне меню:", reply_markup=keyboard)
        await message_or_callback.answer()

@router.message(Command("start"))
async def start_handler(message: Message):
    # Call the common start function
    await start_without_command(message)

@router.message(Command("send_prayer"))
async def send_prayer_command(message: Message, state: FSMContext):
    # Similar to the callback handler, but for command
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Get all categories
    categories = get_all_categories()
    
    # Create keyboard with categories
    buttons = []
    for category_id, category_name in categories:
        buttons.append([InlineKeyboardButton(text=category_name, callback_data=f'category_{category_id}')])
    
    # Add back button
    buttons.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Log user ID for debugging
    user_id = message.from_user.id
    logger.info(f'User {user_id} used /send_prayer command')
    
    await message.answer("Оберіть категорію молитви:", reply_markup=keyboard)
    await state.set_state(PrayerStates.selecting_category)
    logger.info('State set to selecting_category')

@router.message(Command("all_prayers"))
async def all_prayers_command(message: Message):
    # Similar to the callback handler for all prayers
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Get all categories
    categories = get_all_categories()
    
    # Create keyboard with categories
    buttons = []
    for category_id, category_name in categories:
        buttons.append([InlineKeyboardButton(text=category_name, callback_data=f'allprayers_cat_{category_id}')])
    
    # Add "All categories" button
    buttons.append([InlineKeyboardButton(text='Всі', callback_data='allprayers_cat_all')])
    
    # Add back button
    buttons.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    logger.info(f'User {message.from_user.id} used /all_prayers command')
    await message.answer("Оберіть категорію молитв для перегляду:", reply_markup=keyboard)

# Handle any text message from a new user - with lower priority
@router.message(F.text, flags={"low_priority": True})
async def handle_text(message: Message, state: FSMContext):
    # Check if user is already in a specific state
    current_state = await state.get_state()
    
    # Log for debugging
    user_id = message.from_user.id
    logger.info(f'handle_text triggered for user {user_id}. Current state: {current_state}')
    
    # If user is already in a state, let other handlers process the message
    if current_state is not None:
        logger.info(f'User {user_id} is in state {current_state}, skipping generic text handler')
        return
    
    # For any text message from a new user, just show the main menu directly
    logger.info(f'New user {user_id} sent text message, showing main menu directly')
    await start_without_command(message)

# Handler for the Start button press
async def start_without_command(message: Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Надіслати молитву', callback_data='send_pray')],
        [InlineKeyboardButton(text='Показати всі молитви', callback_data='show_all_prayers')],
        [InlineKeyboardButton(text='Показати мої молитви', callback_data='show_my_prayers')],
    ])
    
    await message.answer(
        "Вітаю! Я бот для запису ваших молитов.", 
        reply_markup=keyboard
    )

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback_query: CallbackQuery, state: FSMContext):
    # Сбрасываем состояние если оно есть
    await state.clear()
    # Показываем главное меню
    await show_main_menu(callback_query)

@router.callback_query(F.data == "send_pray")
async def process_callback_send_pray(callback_query: CallbackQuery, state: FSMContext):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    await callback_query.answer(show_alert=False)
    
    # Get all categories
    categories = get_all_categories()
    
    # Create keyboard with categories
    buttons = []
    for category_id, category_name in categories:
        buttons.append([InlineKeyboardButton(text=category_name, callback_data=f'category_{category_id}')])
    
    # Add back button
    buttons.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Log user ID for debugging
    user_id = callback_query.from_user.id
    logger.info(f'User {user_id} is selecting a prayer category')
    
    await callback_query.message.answer("Оберіть категорію молитви:", reply_markup=keyboard)
    await state.set_state(PrayerStates.selecting_category)
    logger.info('State set to selecting_category')

@router.callback_query(PrayerStates.selecting_category, F.data.startswith("category_"))
async def process_category_selection(callback_query: CallbackQuery, state: FSMContext):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    await callback_query.answer(show_alert=False)
    
    # Extract category ID from callback data
    category_id = int(callback_query.data.split("_")[1])
    category_name = get_category_by_id(category_id)
    
    # Log category selection for debugging
    user_id = callback_query.from_user.id
    logger.info(f'User {user_id} selected category: {category_name} (ID: {category_id})')
    
    # Store selected category in state
    await state.update_data(selected_category_id=category_id, selected_category_name=category_name)
    
    # Create keyboard with back button
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
    ])
    
    await callback_query.message.answer(
        f"Ви обрали категорію: <b>{category_name}</b>\nБудь ласка, введіть вашу молитву:",
        reply_markup=keyboard
    )
    
    # Move to next state
    await state.set_state(PrayerStates.expecting_prayer)
    logger.info(f'State set to expecting_prayer for user {user_id}')

@router.message(PrayerStates.expecting_prayer)
async def capture_prayer(message: Message, state: FSMContext):
    # Log entry into the handler for debugging
    logger.info(f'CAPTURE_PRAYER HANDLER TRIGGERED for user {message.from_user.id} with text "{message.text[:20]}..."')
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id = message.from_user.id
    username = message.from_user.username or 'unknown'
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    prayer_text = message.text
    
    logger.info(f'Received prayer text from user {user_id}')
    
    # Get state data
    state_data = await state.get_data()
    logger.info(f'State data: {state_data}')

    # Check if we're editing an existing prayer
    if 'edit_prayer_id' in state_data:
        prayer_id = state_data['edit_prayer_id']
        
        # Check if we need to update the category
        category_id = state_data.get('selected_category_id', None)
        
        logger.info(f'Updating prayer {prayer_id} for user {user_id}')
        
        # Обновляем молитву в БД
        update_prayer(prayer_id, prayer_text, category_id)
        
        # Добавляем кнопку возврата в главное меню
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        # Показываем информацию о том, что было обновлено
        await message.answer(
            f"✅ <b>Молитву оновлено!</b>",
            reply_markup=keyboard
        )
    else:
        # Get selected category from state
        category_id = state_data.get('selected_category_id')
        category_name = state_data.get('selected_category_name', 'Невідома')
        
        logger.info(f'Inserting new prayer for user {user_id} in category {category_name} (ID: {category_id})')
        
        # Insert new prayer with category
        insert_prayer(user_id, username, prayer_text, category_id, first_name, last_name)
        
        # Add "Надіслати молитву" button and the main menu button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Надіслати ще молитву', callback_data='send_pray')],
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await message.answer(
            f"✅ <b>Молитву записано в категорії {category_name}.</b>",
            reply_markup=keyboard
        )

    logger.info(f'Clearing state for user {user_id}')
    await state.clear()

@router.message(Command("my_prayers"))
async def my_prayers(message: Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id = message.from_user.id
    logger.info('Fetching prayers for user_id: %s', user_id)
    prayers = fetch_prayers(user_id)
    
    if not prayers:
        # Добавляем кнопку возврата в главное меню
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await message.answer('У вас немає записаних молитов.', reply_markup=keyboard)
        return

    # Telegram message length limit (4096 characters)
    MAX_MESSAGE_LENGTH = 4000  # Slightly less than the limit for safety
    
    # Показываем все молитвы
    for prayer_id, prayer_text, category_name in prayers:
        # Создаем клавиатуру для действий с молитвой
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='Редагувати', callback_data=f'edit_{prayer_id}'),
                InlineKeyboardButton(text='Видалити', callback_data=f'delete_{prayer_id}')
            ]
        ])
        
        # Add category to message
        category_info = f"<b>Категорія: {category_name or 'Не вказана'}</b>\n\n"
        
        # Проверяем длину сообщения
        if len(prayer_text) + len(category_info) <= MAX_MESSAGE_LENGTH:
            # Если сообщение не слишком длинное, отправляем его полностью с клавиатурой
            await message.answer(f"{category_info}{prayer_text}", reply_markup=keyboard)
        else:
            # Если сообщение слишком длинное, разбиваем его на части
            # Отправляем сначала заголовок с категорией
            await message.answer(category_info)
            
            # Разбиваем длинный текст на части
            remaining_text = prayer_text
            part_number = 1
            total_parts = (len(prayer_text) + MAX_MESSAGE_LENGTH - 1) // MAX_MESSAGE_LENGTH
            
            while remaining_text:
                # Вычисляем размер следующей части
                chunk_size = min(MAX_MESSAGE_LENGTH, len(remaining_text))
                # Извлекаем часть текста
                chunk = remaining_text[:chunk_size]
                # Обновляем оставшийся текст
                remaining_text = remaining_text[chunk_size:]
                
                # Добавляем информацию о части сообщения
                part_info = f"<i>Частина {part_number}/{total_parts}</i>\n\n" if total_parts > 1 else ""
                
                # Отправляем последнюю часть с клавиатурой, остальные без клавиатуры
                if not remaining_text:  # Если это последняя часть
                    await message.answer(f"{part_info}{chunk}", reply_markup=keyboard)
                else:
                    await message.answer(f"{part_info}{chunk}")
                
                part_number += 1
    
    # Отдельное сообщение с кнопкой возврата в главное меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
    ])
    await message.answer('⬆️ Ваші молитви ⬆️', reply_markup=keyboard)

@router.callback_query(F.data.startswith(('edit_', 'delete_')))
async def prayer_callback(callback_query: CallbackQuery, state: FSMContext):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    await callback_query.answer(show_alert=False)
    data = callback_query.data

    if data.startswith('edit_'):
        prayer_id = int(data.split('_')[1])
        result = get_prayer_by_id(prayer_id)
        
        if result:
            prayer_text, category_id, category_name = result
            
            # Проверяем длину молитвы для редактирования
            if len(prayer_text) > 3072:
                # Молитва слишком длинная для редактирования в Telegram
                # Создаем клавиатуру с кнопками для удаления и возврата в меню
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text='Видалити цю молитву', callback_data=f'delete_{prayer_id}'),
                        InlineKeyboardButton(text='Скасувати', callback_data='cancel_edit')
                    ],
                    [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
                ])
                
                # Отправляем предупреждение пользователю
                await callback_query.message.answer(
                    text=f"⚠️ <b>Ця молитва занадто довга для редагування</b>\n\n"
                         f"Через обмеження Telegram, дуже довгі молитви неможливо редагувати.\n"
                         f"Ви можете видалити цю молитву та створити нову замість неї.",
                    reply_markup=keyboard
                )
            else:
                # Offer to choose a new category or keep the existing one
                categories = get_all_categories()
                
                # Create keyboard with categories and cancel button
                buttons = []
                for cat_id, cat_name in categories:
                    if cat_id == category_id:
                        # Mark the current category
                        buttons.append([InlineKeyboardButton(text=f"✓ {cat_name}", callback_data=f'editcat_{prayer_id}_{cat_id}')])
                    else:
                        buttons.append([InlineKeyboardButton(text=cat_name, callback_data=f'editcat_{prayer_id}_{cat_id}')])
                
                buttons.append([InlineKeyboardButton(text='Скасувати', callback_data='cancel_edit')])
                buttons.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
                
                # Отправляем сообщение с выбором категории
                await callback_query.message.answer(
                    text=f"✏️ <b>Редагування молитви</b>\n\n"
                         f"Поточна категорія: <b>{category_name or 'Не вказана'}</b>\n\n"
                         f"Оберіть нову категорію або залиште поточну:",
                    reply_markup=keyboard
                )
        else:
            # Молитва не найдена
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
            ])
            
            await callback_query.message.answer(
                text='Вибачте, молитву не знайдено.',
                reply_markup=keyboard
            )

    elif data.startswith('delete_'):
        prayer_id = int(data.split('_')[1])
        delete_prayer(prayer_id)
        
        # Добавляем кнопку возврата в главное меню
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await callback_query.message.answer(
            text='Молитву видалено.',
            reply_markup=keyboard
        )

@router.callback_query(F.data.startswith("editcat_"))
async def edit_prayer_category(callback_query: CallbackQuery, state: FSMContext):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Parse the callback data to get prayer_id and category_id
    _, prayer_id, category_id = callback_query.data.split("_")
    prayer_id = int(prayer_id)
    category_id = int(category_id)
    
    # Get the category name
    category_name = get_category_by_id(category_id)
    
    # Get the prayer text
    result = get_prayer_by_id(prayer_id)
    if result:
        prayer_text = result[0]
        
        # Store the prayer ID and category in state
        await state.update_data(
            edit_prayer_id=prayer_id,
            selected_category_id=category_id,
            selected_category_name=category_name
        )
        
        # Create keyboard with back button
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Скасувати', callback_data='cancel_edit')],
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        # Отправляем сообщение с текущим текстом и инструкцией
        await callback_query.message.answer(
            text=f"✏️ <b>Редагування молитви в категорії {category_name}</b>\n\n"
                 f"{prayer_text}\n\n"
                 f"<i>Будь ласка, надішліть новий текст молитви або натисніть Скасувати.</i>",
            reply_markup=keyboard
        )
        
        # Set state to expect prayer text
        await state.set_state(PrayerStates.expecting_prayer)
    else:
        # Prayer not found
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await callback_query.message.answer(
            text='Вибачте, молитву не знайдено.',
            reply_markup=keyboard
        )
    
    await callback_query.answer(show_alert=False)

@router.callback_query(F.data == "cancel_edit")
async def cancel_edit(callback_query: CallbackQuery, state: FSMContext):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    await state.clear()
    await callback_query.answer("Редагування скасовано", show_alert=True)
    
    # Добавляем кнопку возврата в главное меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
    ])
    
    await callback_query.message.answer(
        "Редагування молитви скасовано.",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "show_my_prayers")
async def show_my_prayers(callback_query: CallbackQuery):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Get all categories
    categories = get_all_categories()
    
    # Create keyboard with categories
    buttons = []
    for category_id, category_name in categories:
        buttons.append([InlineKeyboardButton(text=category_name, callback_data=f'myprayers_cat_{category_id}')])
    
    # Add "All categories" button
    buttons.append([InlineKeyboardButton(text='Всі', callback_data='myprayers_cat_all')])
    
    # Add back button
    buttons.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.answer("Оберіть категорію молитв для перегляду:", reply_markup=keyboard)
    await callback_query.answer(show_alert=False)

@router.callback_query(F.data.startswith("myprayers_cat_"))
async def show_my_prayers_by_category(callback_query: CallbackQuery):
    category_param = callback_query.data.split("_")[-1]
    
    if category_param == 'all':
        # Show all prayers from user (using pagination)
        await show_my_prayers_page(callback_query, 0)
    else:
        # Show prayers from specific category
        category_id = int(category_param)
        await show_my_prayers_page_by_category(callback_query, category_id, 0)

# Function to show user's prayers with pagination
async def show_my_prayers_page(callback_query: CallbackQuery, offset=0, batch_size=5):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id = callback_query.from_user.id
    logger.info(f'Fetching user prayers with offset={offset}, batch_size={batch_size}')
    
    # Count total prayers from this user
    cursor.execute('SELECT COUNT(*) FROM prayers WHERE user_id = ?', (user_id,))
    total_prayers = cursor.fetchone()[0]
    
    if total_prayers == 0:
        # If no prayers
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='↩️ Назад до категорій', callback_data='show_my_prayers')],
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await callback_query.message.answer(
            'У вас немає записаних молитов.',
            reply_markup=keyboard
        )
        await callback_query.answer(show_alert=False)
        return
    
    # Get prayers with pagination for this user
    cursor.execute('''
    SELECT p.id, p.prayer, c.name
    FROM prayers p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.user_id = ?
    ORDER BY p.created_at DESC
    LIMIT ? OFFSET ?
    ''', (user_id, batch_size, offset))
    prayers = cursor.fetchall()
    
    # Telegram message length limit (4096 characters)
    MAX_MESSAGE_LENGTH = 4000  # Slightly less than the limit for safety
    
    # Show prayers from current page
    for prayer_id, prayer_text, category_name in prayers:
        # Create keyboard for actions with prayer
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='Редагувати', callback_data=f'edit_{prayer_id}'),
                InlineKeyboardButton(text='Видалити', callback_data=f'delete_{prayer_id}')
            ]
        ])
        
        # Add category to message
        category_info = f"<b>Категорія: {category_name or 'Не вказана'}</b>\n\n"
        
        # Check message length
        if len(prayer_text) + len(category_info) <= MAX_MESSAGE_LENGTH:
            # If message is not too long, send it completely with keyboard
            await callback_query.message.answer(f"{category_info}{prayer_text}", reply_markup=keyboard)
        else:
            # If message is too long, split it into parts
            # Send header with category first
            await callback_query.message.answer(category_info)
            
            # Split long text into parts
            remaining_text = prayer_text
            part_number = 1
            total_parts = (len(prayer_text) + MAX_MESSAGE_LENGTH - 1) // MAX_MESSAGE_LENGTH
            
            while remaining_text:
                # Calculate size of next part
                chunk_size = min(MAX_MESSAGE_LENGTH, len(remaining_text))
                # Extract part of text
                chunk = remaining_text[:chunk_size]
                # Update remaining text
                remaining_text = remaining_text[chunk_size:]
                
                # Add information about part of message
                part_info = f"<i>Частина {part_number}/{total_parts}</i>\n\n" if total_parts > 1 else ""
                
                # Send last part with keyboard, others without keyboard
                if not remaining_text:  # If this is the last part
                    await callback_query.message.answer(f"{part_info}{chunk}", reply_markup=keyboard)
                else:
                    await callback_query.message.answer(f"{part_info}{chunk}")
                
                part_number += 1
    
    # Create navigation buttons
    nav_buttons = []
    
    # "Back" button if this is not the first page
    if offset > 0:
        prev_offset = max(0, offset - batch_size)
        nav_buttons.append(
            InlineKeyboardButton(text='⬅️ Попередні', callback_data=f'myprayers_page_{prev_offset}')
        )
    
    # "Next" button if there are more prayers
    if offset + batch_size < total_prayers:
        next_offset = offset + batch_size
        nav_buttons.append(
            InlineKeyboardButton(text='Наступні ➡️', callback_data=f'myprayers_page_{next_offset}')
        )
    
    # Page information
    start_idx = offset + 1
    end_idx = min(offset + batch_size, total_prayers)
    page_info = f"Ваші молитви {start_idx}-{end_idx} з {total_prayers}"
    
    # Form keyboard
    keyboard_rows = []
    if nav_buttons:
        keyboard_rows.append(nav_buttons)
    keyboard_rows.append([InlineKeyboardButton(text='↩️ Назад до категорій', callback_data='show_my_prayers')])
    keyboard_rows.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    # Send message with navigation and page information
    await callback_query.message.answer(page_info, reply_markup=keyboard)
    
    # Answer callback_query to remove loading clock
    await callback_query.answer(show_alert=False)

# Function to show user's prayers from specific category with pagination
async def show_my_prayers_page_by_category(callback_query: CallbackQuery, category_id, offset=0, batch_size=5):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id = callback_query.from_user.id
    category_name = get_category_by_id(category_id)
    logger.info(f'Fetching user prayers for category_id={category_id} with offset={offset}, batch_size={batch_size}')
    
    # Count prayers from this user in this category
    cursor.execute('SELECT COUNT(*) FROM prayers WHERE user_id = ? AND category_id = ?', (user_id, category_id))
    total_prayers = cursor.fetchone()[0]
    
    if total_prayers == 0:
        # If no prayers in this category
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='↩️ Назад до категорій', callback_data='show_my_prayers')],
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await callback_query.message.answer(
            f'У вас немає записаних молитов в категорії {category_name}.',
            reply_markup=keyboard
        )
        await callback_query.answer(show_alert=False)
        return
    
    # Get prayers with pagination for this user and category
    cursor.execute('''
    SELECT p.id, p.prayer, c.name
    FROM prayers p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.user_id = ? AND p.category_id = ?
    ORDER BY p.created_at DESC
    LIMIT ? OFFSET ?
    ''', (user_id, category_id, batch_size, offset))
    prayers = cursor.fetchall()
    
    # Telegram message length limit (4096 characters)
    MAX_MESSAGE_LENGTH = 4000  # Slightly less than the limit for safety
    
    # Show prayers from current page
    for prayer_id, prayer_text, category_name in prayers:
        # Create keyboard for actions with prayer
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='Редагувати', callback_data=f'edit_{prayer_id}'),
                InlineKeyboardButton(text='Видалити', callback_data=f'delete_{prayer_id}')
            ]
        ])
        
        # Add category to message
        category_info = f"<b>Категорія: {category_name or 'Не вказана'}</b>\n\n"
        
        # Check message length
        if len(prayer_text) + len(category_info) <= MAX_MESSAGE_LENGTH:
            # If message is not too long, send it completely with keyboard
            await callback_query.message.answer(f"{category_info}{prayer_text}", reply_markup=keyboard)
        else:
            # If message is too long, split it into parts
            # Send header with category first
            await callback_query.message.answer(category_info)
            
            # Split long text into parts
            remaining_text = prayer_text
            part_number = 1
            total_parts = (len(prayer_text) + MAX_MESSAGE_LENGTH - 1) // MAX_MESSAGE_LENGTH
            
            while remaining_text:
                # Calculate size of next part
                chunk_size = min(MAX_MESSAGE_LENGTH, len(remaining_text))
                # Extract part of text
                chunk = remaining_text[:chunk_size]
                # Update remaining text
                remaining_text = remaining_text[chunk_size:]
                
                # Add information about part of message
                part_info = f"<i>Частина {part_number}/{total_parts}</i>\n\n" if total_parts > 1 else ""
                
                # Send last part with keyboard, others without keyboard
                if not remaining_text:  # If this is the last part
                    await callback_query.message.answer(f"{part_info}{chunk}", reply_markup=keyboard)
                else:
                    await callback_query.message.answer(f"{part_info}{chunk}")
                
                part_number += 1
    
    # Create navigation buttons
    nav_buttons = []
    
    # "Back" button if this is not the first page
    if offset > 0:
        prev_offset = max(0, offset - batch_size)
        nav_buttons.append(
            InlineKeyboardButton(text='⬅️ Попередні', callback_data=f'mycat_page_{category_id}_{prev_offset}')
        )
    
    # "Next" button if there are more prayers
    if offset + batch_size < total_prayers:
        next_offset = offset + batch_size
        nav_buttons.append(
            InlineKeyboardButton(text='Наступні ➡️', callback_data=f'mycat_page_{category_id}_{next_offset}')
        )
    
    # Page information
    start_idx = offset + 1
    end_idx = min(offset + batch_size, total_prayers)
    page_info = f"Ваші молитви {start_idx}-{end_idx} з {total_prayers} в категорії {category_name}"
    
    # Form keyboard
    keyboard_rows = []
    if nav_buttons:
        keyboard_rows.append(nav_buttons)
    keyboard_rows.append([InlineKeyboardButton(text='↩️ Назад до категорій', callback_data='show_my_prayers')])
    keyboard_rows.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    # Send message with navigation and page information
    await callback_query.message.answer(page_info, reply_markup=keyboard)
    
    # Answer callback_query to remove loading clock
    await callback_query.answer(show_alert=False)

# Handler for switching between user prayer pages
@router.callback_query(F.data.startswith("myprayers_page_"))
async def handle_my_prayers_pagination(callback_query: CallbackQuery):
    # Extract page number from callback_data
    offset = int(callback_query.data.split("_")[-1])
    # Show next page
    await show_my_prayers_page(callback_query, offset)

# Handler for switching between user prayer pages by category
@router.callback_query(F.data.startswith("mycat_page_"))
async def handle_my_category_prayer_pagination(callback_query: CallbackQuery):
    # Extract category_id and page number from callback_data
    parts = callback_query.data.split("_")
    category_id = int(parts[2])
    offset = int(parts[3])
    # Show next page for specific category
    await show_my_prayers_page_by_category(callback_query, category_id, offset)

@router.callback_query(F.data == "show_all_prayers")
async def show_all_prayers(callback_query: CallbackQuery):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    # Get all categories
    categories = get_all_categories()
    
    # Create keyboard with categories
    buttons = []
    for category_id, category_name in categories:
        buttons.append([InlineKeyboardButton(text=category_name, callback_data=f'allprayers_cat_{category_id}')])
    
    # Add "All categories" button
    buttons.append([InlineKeyboardButton(text='Всі', callback_data='allprayers_cat_all')])
    
    # Add back button
    buttons.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.answer("Оберіть категорію молитв для перегляду:", reply_markup=keyboard)
    await callback_query.answer(show_alert=False)

@router.callback_query(F.data.startswith("allprayers_cat_"))
async def show_all_prayers_by_category(callback_query: CallbackQuery):
    category_param = callback_query.data.split("_")[-1]
    
    if category_param == 'all':
        # Show all prayers from all categories (using existing pagination)
        await show_prayers_page(callback_query, 0)
    else:
        # Show prayers from specific category
        category_id = int(category_param)
        await show_prayers_page_by_category(callback_query, category_id, 0)

# Modified function to show prayers with pagination filtered by category
async def show_prayers_page_by_category(callback_query: CallbackQuery, category_id, offset=0, batch_size=5):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    category_name = get_category_by_id(category_id)
    logger.info(f'Fetching prayers for category_id={category_id} with offset={offset}, batch_size={batch_size}')
    
    # Count prayers in this category
    total_prayers = count_prayers_by_category(category_id)
    
    if total_prayers == 0:
        # If no prayers in this category
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='↩️ Назад до категорій', callback_data='show_all_prayers')],
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await callback_query.message.answer(
            f'Поки що немає жодної молитви в категорії {category_name}.',
            reply_markup=keyboard
        )
        await callback_query.answer(show_alert=False)
        return
    
    # Get prayers with pagination for specific category
    prayers = fetch_all_prayers_by_category(category_id, limit=batch_size, offset=offset)
    
    # Telegram message length limit (4096 characters)
    MAX_MESSAGE_LENGTH = 4000  # Slightly less than the limit for safety
    
    # Show prayers from current page
    for prayer in prayers:
        prayer_text = prayer[0]  # Prayer text is first element
        category_name = prayer[5] if len(prayer) > 5 else "Не вказана"  # Category is sixth element
        
        # Get name and surname, or use username if they don't exist
        author = "Анонім"
        
        # Check first_name and last_name fields
        if len(prayer) > 3:  # If first_name exists
            first_name = prayer[3] if prayer[3] else ""
            last_name = ""
            if len(prayer) > 4:  # If last_name exists
                last_name = prayer[4] if prayer[4] else ""
            
            # If name or surname exists, use them
            if first_name or last_name:
                author = f"{first_name} {last_name}".strip()
        
        # If author couldn't be formed from name and surname, use username
        if author == "Анонім" and prayer[1]:
            author = prayer[1]
        
        # Format date if it exists
        created_at = ""
        if len(prayer) > 2 and prayer[2]:
            try:
                # Try to convert date string to datetime object
                date_obj = datetime.fromisoformat(prayer[2])
                # Format date to more readable form
                created_at = f" ({date_obj.strftime('%d.%m.%Y')})"
            except:
                # If date couldn't be converted, ignore
                pass
        
        # Format message header
        header = f"<b>Молитва від {author}{created_at}</b>\n<b>Категорія: {category_name}</b>\n\n"
        
        # Check message length
        if len(prayer_text) + len(header) <= MAX_MESSAGE_LENGTH:
            # If message is not too long, send it completely
            await callback_query.message.answer(f"{header}{prayer_text}")
        else:
            # If message is too long, split it into parts
            # Send header first
            await callback_query.message.answer(header)
            
            # Split long text into parts
            remaining_text = prayer_text
            part_number = 1
            total_parts = (len(prayer_text) + MAX_MESSAGE_LENGTH - 1) // MAX_MESSAGE_LENGTH
            
            while remaining_text:
                # Calculate size of next part
                chunk_size = min(MAX_MESSAGE_LENGTH, len(remaining_text))
                # Extract part of text
                chunk = remaining_text[:chunk_size]
                # Update remaining text
                remaining_text = remaining_text[chunk_size:]
                
                # Add information about part of message
                part_info = f"<i>Частина {part_number}/{total_parts}</i>\n\n" if total_parts > 1 else ""
                await callback_query.message.answer(f"{part_info}{chunk}")
                part_number += 1
    
    # Create navigation buttons
    nav_buttons = []
    
    # "Back" button if this is not the first page
    if offset > 0:
        prev_offset = max(0, offset - batch_size)
        nav_buttons.append(
            InlineKeyboardButton(text='⬅️ Попередні', callback_data=f'cat_page_{category_id}_{prev_offset}')
        )
    
    # "Next" button if there are more prayers
    if offset + batch_size < total_prayers:
        next_offset = offset + batch_size
        nav_buttons.append(
            InlineKeyboardButton(text='Наступні ➡️', callback_data=f'cat_page_{category_id}_{next_offset}')
        )
    
    # Page information
    start_idx = offset + 1
    end_idx = min(offset + batch_size, total_prayers)
    page_info = f"Молитви {start_idx}-{end_idx} з {total_prayers} в категорії {category_name}"
    
    # Form keyboard
    keyboard_rows = []
    if nav_buttons:
        keyboard_rows.append(nav_buttons)
    keyboard_rows.append([InlineKeyboardButton(text='↩️ Назад до категорій', callback_data='show_all_prayers')])
    keyboard_rows.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    # Send message with navigation and page information
    await callback_query.message.answer(page_info, reply_markup=keyboard)
    
    # Answer callback_query to remove loading clock
    await callback_query.answer(show_alert=False)

# Handler for switching between prayer pages by category
@router.callback_query(F.data.startswith("cat_page_"))
async def handle_category_prayer_pagination(callback_query: CallbackQuery):
    # Extract category_id and page number from callback_data
    parts = callback_query.data.split("_")
    category_id = int(parts[2])
    offset = int(parts[3])
    # Show next page for specific category
    await show_prayers_page_by_category(callback_query, category_id, offset)

@router.callback_query(F.data.startswith("prayers_page_"))
async def handle_prayer_pagination(callback_query: CallbackQuery):
    # Извлекаем номер страницы из callback_data
    offset = int(callback_query.data.split("_")[-1])
    # Показываем следующую страницу
    await show_prayers_page(callback_query, offset)

# Функция для постепенного отображения всех молитв с пагинацией
async def show_prayers_page(callback_query: CallbackQuery, offset=0, batch_size=5):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    logger.info(f'Fetching prayers with offset={offset}, batch_size={batch_size}')
    
    # Получаем общее количество молитв для пагинации
    total_prayers = count_all_prayers()
    
    if total_prayers == 0:
        # Если молитв нет
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='↩️ Назад до категорій', callback_data='show_all_prayers')],
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await callback_query.message.answer(
            'Поки що немає жодної молитви.',
            reply_markup=keyboard
        )
        await callback_query.answer(show_alert=False)
        return
    
    # Получаем часть молитв с пагинацией
    prayers = fetch_all_prayers(limit=batch_size, offset=offset)
    
    # Telegram message length limit (4096 characters)
    MAX_MESSAGE_LENGTH = 4000  # Slightly less than the limit for safety
    
    # Показываем молитвы из текущей страницы
    for prayer in prayers:
        prayer_text = prayer[0]  # Текст молитвы - первый элемент
        category_name = prayer[5] if len(prayer) > 5 else "Не вказана"  # Category is the sixth element
        
        # Получаем имя и фамилию, или используем username, если их нет
        author = "Анонім"
        
        # Проверяем наличие полей first_name и last_name
        if len(prayer) > 3:  # Если есть поля first_name
            first_name = prayer[3] if prayer[3] else ""
            last_name = ""
            if len(prayer) > 4:  # Если есть поле last_name
                last_name = prayer[4] if prayer[4] else ""
            
            # Если есть имя или фамилия, используем их
            if first_name or last_name:
                author = f"{first_name} {last_name}".strip()
        
        # Если не удалось сформировать автора из имени и фамилии, используем username
        if author == "Анонім" and prayer[1]:
            author = prayer[1]
        
        # Форматируем дату, если она есть
        created_at = ""
        if len(prayer) > 2 and prayer[2]:
            try:
                # Попытка преобразовать строку даты в объект datetime
                date_obj = datetime.fromisoformat(prayer[2])
                # Форматирование даты в более читаемый вид
                created_at = f" ({date_obj.strftime('%d.%m.%Y')})"
            except:
                # Если не удалось преобразовать дату, игнорируем
                pass
        
        # Формируем заголовок сообщения
        header = f"<b>Молитва від {author}{created_at}</b>\n<b>Категорія: {category_name}</b>\n\n"
        
        # Проверяем длину сообщения
        if len(prayer_text) + len(header) <= MAX_MESSAGE_LENGTH:
            # Если сообщение не слишком длинное, отправляем его полностью
            await callback_query.message.answer(f"{header}{prayer_text}")
        else:
            # Если сообщение слишком длинное, разбиваем его на части
            # Отправляем сначала заголовок
            await callback_query.message.answer(header)
            
            # Разбиваем длинный текст на части
            remaining_text = prayer_text
            part_number = 1
            total_parts = (len(prayer_text) + MAX_MESSAGE_LENGTH - 1) // MAX_MESSAGE_LENGTH
            
            while remaining_text:
                # Вычисляем размер следующей части
                chunk_size = min(MAX_MESSAGE_LENGTH, len(remaining_text))
                # Извлекаем часть текста
                chunk = remaining_text[:chunk_size]
                # Обновляем оставшийся текст
                remaining_text = remaining_text[chunk_size:]
                
                # Добавляем информацию о части сообщения
                part_info = f"<i>Частина {part_number}/{total_parts}</i>\n\n" if total_parts > 1 else ""
                await callback_query.message.answer(f"{part_info}{chunk}")
                part_number += 1
    
    # Создаем кнопки навигации
    nav_buttons = []
    
    # Кнопка "Назад" если это не первая страница
    if offset > 0:
        prev_offset = max(0, offset - batch_size)
        nav_buttons.append(
            InlineKeyboardButton(text='⬅️ Попередні', callback_data=f'prayers_page_{prev_offset}')
        )
    
    # Кнопка "Далее" если есть еще молитвы
    if offset + batch_size < total_prayers:
        next_offset = offset + batch_size
        nav_buttons.append(
            InlineKeyboardButton(text='Наступні ➡️', callback_data=f'prayers_page_{next_offset}')
        )
    
    # Информация о странице
    start_idx = offset + 1
    end_idx = min(offset + batch_size, total_prayers)
    page_info = f"Молитви {start_idx}-{end_idx} з {total_prayers}"
    
    # Формируем клавиатуру
    keyboard_rows = []
    if nav_buttons:
        keyboard_rows.append(nav_buttons)
    keyboard_rows.append([InlineKeyboardButton(text='↩️ Назад до категорій', callback_data='show_all_prayers')])
    keyboard_rows.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    # Отправляем сообщение с навигацией и информацией о странице
    await callback_query.message.answer(page_info, reply_markup=keyboard)
    
    # Отвечаем на callback_query, чтобы убрать часы загрузки
    await callback_query.answer(show_alert=False)

def register_handlers(dp: Dispatcher):
    # Log the handlers registration
    logger.info('Registering message handlers')
    
    # Create a new router with proper priority for message handlers
    priority_router = Router()
    
    # Add the PrayerStates.expecting_prayer handler first (high priority)
    priority_router.message.register(capture_prayer, PrayerStates.expecting_prayer)
    
    # Add the generic text handler last (low priority)
    priority_router.message.register(handle_text, F.text)
    
    # Include the priority router first
    dp.include_router(priority_router)
    
    # Include the main router
    dp.include_router(router)
