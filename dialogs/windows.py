from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.kbd import Button, Row, Column, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput
from .states import PrayerDialog
from services import insert_prayer, fetch_prayers, update_prayer, delete_prayer, get_prayer_by_id
import logging

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4096
PREVIEW_LENGTH = 100

def split_long_message(text):
    """Split message into chunks of maximum 4096 characters."""
    return [text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]

async def send_long_text(message, text, prefix=""):
    """Helper function to send long text in multiple messages."""
    parts = split_long_message(text)
    for i, part in enumerate(parts):
        if i < len(parts) - 1:
            await message.answer(f"{prefix}Частина {i+1}:\n{part}")
        else:
            await message.answer(f"{prefix}Частина {i+1} (остання):\n{part}")

def get_preview_text(text):
    """Get a preview of the text that's safe to display."""
    if not text:
        return ""
    if len(text) <= PREVIEW_LENGTH:
        return text
    return text[:PREVIEW_LENGTH] + "..."

async def on_prayer_selected(c, button, manager):
    prayer_id = int(button.id)
    await manager.switch_to(PrayerDialog.EDIT_PRAYER)
    await manager.update({'prayer_id': prayer_id})

async def on_delete_prayer(c, button, manager):
    prayer_id = int(c.data)
    delete_prayer(prayer_id)
    await manager.switch_to(PrayerDialog.LIST_PRAYERS)

async def handle_delete_current(c, b, manager):
    prayer_id = manager.current_context().dialog_data.get('prayer_id')
    if prayer_id:
        delete_prayer(prayer_id)
    await manager.switch_to(PrayerDialog.LIST_PRAYERS)

async def on_edit_prayer(c, widget, manager, item):
    logger.info(f"Edit prayer called with item: {item}")
    try:
        # Get the prayer details from the database
        prayer_id = item
        prayer = get_prayer_by_id(int(prayer_id))
        if not prayer:
            logger.error(f"Prayer not found for id: {prayer_id}")
            return
            
        # Store only the ID in dialog data
        await manager.update({
            'prayer_id': int(prayer_id)
        })
        
        # Send the prayer text as a separate message
        await c.message.answer("Поточний текст молитви:")
        if len(prayer) > MAX_MESSAGE_LENGTH:
            await send_long_text(c.message, prayer)
        else:
            await c.message.answer(prayer)
            
        await c.message.answer("⬆️ Надішліть нову версію молитви:")
        await manager.switch_to(PrayerDialog.EDIT_PRAYER)
    except Exception as e:
        logger.error(f"Error in on_edit_prayer: {e}")
        raise

async def on_prayer_message(m, dialog, manager):
    user_id = m.from_user.id
    username = m.from_user.username or 'unknown'
    prayer_text = m.text
    
    # Split message if it's too long
    if len(prayer_text) > MAX_MESSAGE_LENGTH:
        parts = split_long_message(prayer_text)
        # Store the combined text in the database
        if manager.current_context().state == PrayerDialog.EDIT_PRAYER:
            prayer_id = manager.current_context().dialog_data.get('prayer_id')
            if prayer_id:
                update_prayer(prayer_id, prayer_text)
        else:
            insert_prayer(user_id, username, prayer_text)
        
        # Send each part as a separate message
        for part in parts[:-1]:
            await m.answer(f"Частина молитви:\n{part}")
        # Send the last part with confirmation
        await m.answer(f"Остання частина молитви:\n{parts[-1]}\n\nМолитва збережена!")
    else:
        # Handle normal-length message
        if manager.current_context().state == PrayerDialog.EDIT_PRAYER:
            prayer_id = manager.current_context().dialog_data.get('prayer_id')
            if prayer_id:
                update_prayer(prayer_id, prayer_text)
                await m.answer("Молитва оновлена!")
        else:
            insert_prayer(user_id, username, prayer_text)
            await m.answer("Молитва збережена!")
    
    await manager.switch_to(PrayerDialog.MAIN)

async def get_prayers(dialog_manager, **kwargs):
    user_id = dialog_manager.event.from_user.id
    prayers = fetch_prayers(user_id)
    return {
        'prayers': [(str(id), f"🙏 {get_preview_text(text)}") for id, text in prayers]
    }

async def get_edit_data(dialog_manager, **kwargs):
    """Return minimal data for the edit window."""
    return {'text': 'Надішліть нову версію молитви:'}

main_window = Window(
    Const("Вітаємо в Prayer Bot! Що ви хочете зробити?"),
    Column(
        Button(Const("📝 Додати молитву"), id="add", on_click=lambda c, b, m: m.switch_to(PrayerDialog.ADD_PRAYER)),
        Button(Const("📋 Мої молитви"), id="list", on_click=lambda c, b, m: m.switch_to(PrayerDialog.LIST_PRAYERS)),
    ),
    state=PrayerDialog.MAIN
)

add_prayer_window = Window(
    Const("Внести нову молитву:"),
    MessageInput(on_prayer_message),
    SwitchTo(Const("⬅️ Назад"), id="back", state=PrayerDialog.MAIN),
    state=PrayerDialog.ADD_PRAYER
)

list_prayers_window = Window(
    Const("Ваші молитви:\n"),
    Column(
        Select(
            Format("{item[1]}"),
            id="prayers",
            items="prayers",
            item_id_getter=lambda x: x[0],
            on_click=on_edit_prayer
        ),
    ),
    Row(
        Button(
            Const("⬅️ Назад"),
            id="back",
            on_click=lambda c, b, m: m.switch_to(PrayerDialog.MAIN)
        ),
    ),
    getter=get_prayers,
    state=PrayerDialog.LIST_PRAYERS
)

edit_prayer_window = Window(
    Format("{text}"),
    MessageInput(on_prayer_message),
    Row(
        Button(
            Const("🗑 Видалити"),
            id="delete_current",
            on_click=handle_delete_current
        ),
        SwitchTo(Const("⬅️ Назад"), id="back", state=PrayerDialog.MAIN),
    ),
    getter=get_edit_data,
    state=PrayerDialog.EDIT_PRAYER
)

__all__ = ['main_window', 'add_prayer_window', 'list_prayers_window', 'edit_prayer_window'] 

