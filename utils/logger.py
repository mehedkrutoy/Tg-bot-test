import logging
from typing import Union
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

def log_user_action(event: Union[Message, CallbackQuery], action: str):
    """Логирование действий пользователя"""
    user_id = event.from_user.id if event.from_user else "Unknown"
    username = event.from_user.username if event.from_user else "Unknown"
    
    logger.info(
        f"User {user_id} (@{username}) performed action: {action}"
    )

def log_error(error: Exception, context: str = ""):
    """Логирование ошибок"""
    logger.error(
        f"Error in {context}: {str(error)}",
        exc_info=True
    ) 