import time
from typing import Union, Dict

message_timestamps: Dict[int, float] = {}

def check_button_lifetime(message_id: int, lifetime: int = 120) -> bool:
    """Проверяет, не истекло ли время жизни кнопки"""
    if message_id not in message_timestamps:
        return False
    return time.time() - message_timestamps[message_id] <= lifetime

def format_money(amount: Union[int, float]) -> str:
    """Форматирует денежную сумму"""
    return f"{amount:.2f}"

def save_message_timestamp(message_id: int):
    """Сохраняет время создания сообщения"""
    message_timestamps[message_id] = time.time()

def clear_old_timestamps(lifetime: int = 120):
    """Очищает старые временные метки"""
    current_time = time.time()
    message_timestamps.clear()
    return {
        msg_id: timestamp 
        for msg_id, timestamp in message_timestamps.items() 
        if current_time - timestamp <= lifetime
    } 