from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    ADD_TIME = State()
    REMOVE_TIME = State()
    CREATE_STATIC_PROFILE = State()
    
    ADD_TIME_USER = State()
    REMOVE_TIME_USER = State()
    ADD_TIME_AMOUNT = State()
    REMOVE_TIME_AMOUNT = State()

    send_message_waiting_text = State()
    send_message_waiting_username = State()

    CREATE_PROMOCODE = State()
