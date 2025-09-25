from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    waiting_promocode = State()