from aiogram.fsm.state import StatesGroup, State

class ReplenishStates(StatesGroup):
    waiting_for_amount = State()

class Form(StatesGroup):
    waiting_for_message = State()
    in_support_chat = State()
    waiting_for_promo = State()

class NumberInput(StatesGroup):
    waiting_for_number = State()

class PaymentStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_receipt = State()
