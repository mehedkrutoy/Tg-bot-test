from dataclasses import dataclass, field
from typing import Dict
from environs import Env

@dataclass
class Config:
    BOT_TOKEN: str
    PAYMENT_TOKEN: str
    BUTTON_LIFETIME: int = 120
    COURSE_RATE: float = 0.65
    GROUP_NEWS: str = "t.me/channel_news"
    GROUP_REVIEWS: str = "t.me/channel_reviews"
    ADMIN_IDS: Dict[int, str] = field(default_factory=lambda: {

        5598123667: "Mehed"
    })
    MODERATOR_CHAT_IDS: Dict[int, str] = field(default_factory=lambda: {
        7074139761: "Модератор #1337"
    })

def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path or '.env')

    return Config(
        BOT_TOKEN=env.str("BOT_TOKEN"),
        PAYMENT_TOKEN=env.str("PAYMENT_TOKEN")
    )

config = load_config()

BOT_TOKEN = config.BOT_TOKEN
