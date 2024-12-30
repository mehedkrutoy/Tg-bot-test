from dataclasses import dataclass, field
from typing import Dict
from environs import Env
import os

@dataclass
class Config:
    BOT_TOKEN: str
    PAYMENT_TOKEN: str
    ADMIN_IDS: Dict[int, str] = field(default_factory=dict)

def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path or '.env')

    admin_ids = {}
    for key in os.environ:
        if key.startswith("ADMIN_"):
            try:
                admin_id = int(key.split("_")[1])
                admin_ids[admin_id] = os.environ[key]
            except (ValueError, IndexError):
                continue

    return Config(
        BOT_TOKEN=env.str("BOT_TOKEN"),
        PAYMENT_TOKEN=env.str("PAYMENT_TOKEN"),
        ADMIN_IDS=admin_ids
    )

config = load_config()
