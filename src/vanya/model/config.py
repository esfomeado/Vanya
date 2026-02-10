from typing import Optional

from pydantic import BaseModel


class AccountConfig(BaseModel):
    username: str
    password: str
    auto_equip: bool = True
    boss_farm: bool = False
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
    proxy: Optional[str] = None


class TelegramConfig(BaseModel):
    token: str
    allowed_users: list[int]


class Config(BaseModel):
    accounts: list[AccountConfig]
    telegram: TelegramConfig
