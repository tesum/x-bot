from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    waiting_promocode = State()
    
    waiting_help_text = State()