from aiogram import Bot, Router, F, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging
from services import insert_prayer, fetch_prayers, update_prayer, delete_prayer, get_prayer_by_id

# Get logger
logger = logging.getLogger(__name__)

# Create router instance
router = Router()

# Define the PrayerStates class
class PrayerStates(StatesGroup):
    expecting_prayer = State()

# Функция для создания главного меню
async def show_main_menu(message_or_callback):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Надіслати молитву', callback_data='send_pray')],
        [InlineKeyboardButton(text='Показати мої молитви', callback_data='show_my_prayers')]
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
        [InlineKeyboardButton(text='Показати мої молитви', callback_data='show_my_prayers')]
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
    
    user_id = callback_query.from_user.id
    await callback_query.answer(show_alert=False)
    
    # Добавляем кнопку возврата в главное меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
    ])
    
    await callback_query.message.answer("Будь ласка, введіть вашу молитву:", reply_markup=keyboard)
    await state.set_state(PrayerStates.expecting_prayer)
    logger.info('State set to expecting_prayer')

@router.message(PrayerStates.expecting_prayer)
async def capture_prayer(message: Message, state: FSMContext):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    user_id = message.from_user.id
    username = message.from_user.username or 'unknown'
    prayer_text = message.text

    # Check if we're editing an existing prayer
    state_data = await state.get_data()
    if 'edit_prayer_id' in state_data:
        prayer_id = state_data['edit_prayer_id']
        
        # Обновляем молитву в БД
        update_prayer(prayer_id, prayer_text)
        
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
        insert_prayer(user_id, username, prayer_text)
        
        # Добавляем кнопку возврата в главное меню
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
        ])
        
        await message.answer("✅ Молитву записано.", reply_markup=keyboard)

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

    # Показываем все молитвы
    for prayer_id, prayer_text in prayers:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='Редагувати', callback_data=f'edit_{prayer_id}'),
                InlineKeyboardButton(text='Видалити', callback_data=f'delete_{prayer_id}')
            ]
        ])
        await message.answer(prayer_text, reply_markup=keyboard)
    
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
        original_text = get_prayer_by_id(prayer_id)
        if original_text:
            # Проверяем длину молитвы для редактирования
            if len(original_text) > 3000:
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
                # Молитва подходящей длины для редактирования
                # Создаем клавиатуру с кнопкой отмены и возврата в меню
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text='Скасувати', callback_data='cancel_edit')],
                    [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
                ])
                
                # Отправляем сообщение с текущим текстом и инструкцией
                await callback_query.message.answer(
                    text=f"✏️ <b>Редагування молитви:</b>\n\n"
                         f"{original_text}\n\n"
                         f"<i>Будь ласка, надішліть новий текст молитви або натисніть Скасувати.</i>",
                    reply_markup=keyboard
                )
                
                # Сохраняем ID молитвы для редактирования в состоянии
                await state.update_data(edit_prayer_id=prayer_id, original_text=original_text)
                await state.set_state(PrayerStates.expecting_prayer)
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

    # Показываем все молитвы
    for prayer_id, prayer_text in prayers:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='Редагувати', callback_data=f'edit_{prayer_id}'),
                InlineKeyboardButton(text='Видалити', callback_data=f'delete_{prayer_id}')
            ]
        ])
        await callback_query.message.answer(prayer_text, reply_markup=keyboard)
    
    # Отдельное сообщение с кнопкой возврата в главное меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🏠 До головного меню', callback_data='main_menu')]
    ])
    await callback_query.message.answer('⬆️ Ваші молитви ⬆️', reply_markup=keyboard)

    await callback_query.answer(show_alert=False)

def register_handlers(dp: Dispatcher):
    # Include the router in the dispatcher
    dp.include_router(router)
