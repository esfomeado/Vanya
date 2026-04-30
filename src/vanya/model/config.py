from typing import Optional

from pydantic import BaseModel


class AccountConfig(BaseModel):
    username: str
    password: str
    auto_equip: bool = True
    boss_farm: bool = False
    proxy: Optional[str] = None


class TelegramConfig(BaseModel):
    token: str
    allowed_users: list[int]


class Config(BaseModel):
    accounts: list[AccountConfig]
    telegram: TelegramConfig
