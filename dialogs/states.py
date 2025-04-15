from aiogram.fsm.state import StatesGroup, State

class PrayerDialog(StatesGroup):
    MAIN = State()
    ADD_PRAYER = State()
    LIST_PRAYERS = State()
    EDIT_PRAYER = State() 