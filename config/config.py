from dataclasses import dataclass, field
from typing import Dict
from environs import Env
import os

@dataclass
class Config:
    BOT_TOKEN: str
    PAYMENT_TOKEN: str
    ADMIN_IDS: Dict[int, str] = field(default_factory=dict)
    MODERATOR_CHAT_IDS: Dict[int, str] = field(default_factory=dict)

def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path or '.env')

    admin_ids = {}
    moderator_ids = {}
    
    for key, value in os.environ.items():
        if key.startswith("ADMIN_"):
            try:
                admin_id = int(value)
                admin_ids[admin_id] = f"Admin #{key.split('_')[1]}"
            except (ValueError, IndexError):
                continue
        elif key.startswith("MOD_"):
            try:
                mod_id = int(value)
                moderator_ids[mod_id] = f"Moderator #{key.split('_')[1]}"
            except (ValueError, IndexError):
                continue

    return Config(
        BOT_TOKEN=env.str("BOT_TOKEN"),
        PAYMENT_TOKEN=env.str("PAYMENT_TOKEN"),
        ADMIN_IDS=admin_ids,
        MODERATOR_CHAT_IDS=moderator_ids
    )

config = load_config()
