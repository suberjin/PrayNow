from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Back
from aiogram_dialog.widgets.text import Const
from .states import PrayerDialog
from .windows import add_prayer_window, list_prayers_window, edit_prayer_window, main_window
from aiogram.types import CallbackQuery

async def get_data(**kwargs):
    return {
        "title": "Prayer Bot"
    }

async def on_add_prayer_click(c: CallbackQuery, button: Button, manager: DialogManager):
    await manager.switch_to(PrayerDialog.ADD_PRAYER)

async def on_list_prayers_click(c: CallbackQuery, button: Button, manager: DialogManager):
    await manager.switch_to(PrayerDialog.LIST_PRAYERS)

main_window = Window(
    Const("Welcome to Prayer Bot! What would you like to do?"),
    Button(
        Const("📝 Add Prayer"), 
        id="send_pray", 
        on_click=on_add_prayer_click
    ),
    Button(
        Const("📋 My Prayers"), 
        id="list", 
        on_click=on_list_prayers_click
    ),
    state=PrayerDialog.MAIN,
    getter=get_data
)

dialog = Dialog(
    main_window,
    add_prayer_window,
    list_prayers_window,
    edit_prayer_window,
)

__all__ = ['dialog', 'PrayerDialog'] 