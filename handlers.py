from aiogram import Bot, Router, F, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
from services import insert_prayer, fetch_prayers, update_prayer, delete_prayer, get_prayer_by_id, fetch_all_prayers, count_all_prayers
from database import get_all_categories, get_category_by_id
from datetime import datetime

# Get logger
logger = logging.getLogger(__name__)

# Create router instance
router = Router()

# Define the PrayerStates class
class PrayerStates(StatesGroup):
    selecting_category = State()
    expecting_prayer = State()

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
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Надіслати молитву', callback_data='send_pray')],
        [InlineKeyboardButton(text='Показати всі молитви', callback_data='show_all_prayers')],
        [InlineKeyboardButton(text='Показати мої молитви', callback_data='show_my_prayers')],
    ])
    await message.answer("Вітаю! Я бот для запису ваших молитов.", reply_markup=keyboard)

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
    logger.info('State set to expecting_prayer')

@router.message(PrayerStates.expecting_prayer)
async def capture_prayer(message: Message, state: FSMContext):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id = message.from_user.id
    username = message.from_user.username or 'unknown'
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    prayer_text = message.text
    
    # Get state data
    state_data = await state.get_data()

    # Check if we're editing an existing prayer
    if 'edit_prayer_id' in state_data:
        prayer_id = state_data['edit_prayer_id']
        
        # Check if we need to update the category
        category_id = state_data.get('selected_category_id', None)
        
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
        
        # Insert new prayer with category
        insert_prayer(user_id, username, prayer_text, category_id, first_name, last_name)
        
        # Добавляем кнопку возврата в главное меню
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await message.answer(
            f"✅ <b>Молитву записано в категорії {category_name}.</b>",
            reply_markup=keyboard
        )

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
    
    user_id = callback_query.from_user.id
    logger.info('Fetching prayers for user_id: %s', user_id)
    prayers = fetch_prayers(user_id)
    
    if not prayers:
        # Добавляем кнопку возврата в главное меню
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await callback_query.message.answer(
            'У вас немає записаних молитов.',
            reply_markup=keyboard
        )
        return

    # Telegram message length limit (4096 characters)
    MAX_MESSAGE_LENGTH = 4000  # Slightly less than the limit for safety
    
    # Показываем все молитвы пользователя
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
            await callback_query.message.answer(f"{category_info}{prayer_text}", reply_markup=keyboard)
        else:
            # Если сообщение слишком длинное, разбиваем его на части
            # Отправляем сначала заголовок с категорией
            await callback_query.message.answer(category_info)
            
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
                    await callback_query.message.answer(f"{part_info}{chunk}", reply_markup=keyboard)
                else:
                    await callback_query.message.answer(f"{part_info}{chunk}")
                
                part_number += 1
    
    # Отдельное сообщение с кнопкой возврата в главное меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
    ])
    await callback_query.message.answer('⬆️ Ваші молитви ⬆️', reply_markup=keyboard)

    await callback_query.answer(show_alert=False)

@router.callback_query(F.data == "show_all_prayers")
async def show_all_prayers(callback_query: CallbackQuery):
    await show_prayers_page(callback_query, 0)

# Функция для постепенного отображения всех молитв с пагинацией
async def show_prayers_page(callback_query: CallbackQuery, offset=0, batch_size=5):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    logger.info(f'Fetching prayers with offset={offset}, batch_size={batch_size}')
    
    # Получаем общее количество молитв для пагинации
    total_prayers = count_all_prayers()
    
    if total_prayers == 0:
        # Если молитв нет
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
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
    keyboard_rows.append([InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    # Отправляем сообщение с навигацией и информацией о странице
    await callback_query.message.answer(page_info, reply_markup=keyboard)
    
    # Отвечаем на callback_query, чтобы убрать часы загрузки
    await callback_query.answer(show_alert=False)

# Обработчик для переключения между страницами молитв
@router.callback_query(F.data.startswith("prayers_page_"))
async def handle_prayer_pagination(callback_query: CallbackQuery):
    # Извлекаем номер страницы из callback_data
    offset = int(callback_query.data.split("_")[-1])
    # Показываем следующую страницу
    await show_prayers_page(callback_query, offset)

def register_handlers(dp: Dispatcher):
    # Include the router in the dispatcher
    dp.include_router(router)
