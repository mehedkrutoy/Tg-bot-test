from aiogram import Dispatcher
from . import admin, user, support, payments

def register_all_handlers(dp: Dispatcher):
    handlers = [
        admin.router,
        support.router,
        payments.router,
        user.router,  # user router должен быть последним
    ]
    
    for handler in handlers:
        dp.include_router(handler) 