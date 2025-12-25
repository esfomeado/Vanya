from pydantic import BaseModel


class AccountConfig(BaseModel):
    username: str
    password: str
    auto_equip: bool = True


class TelegramConfig(BaseModel):
    token: str
    allowed_users: list[int]


class Config(BaseModel):
    accounts: list[AccountConfig]
    telegram: TelegramConfig
