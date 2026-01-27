from typing import Optional

import httpx
from httpx import Client

from src.vanya.model.config import AccountConfig
from src.vanya.model.hunt import Hunt
from src.vanya.model.mode import Mode


class Stats:
    def __init__(self):
        self.bow: int = 0
        self.defence: int = 0
        self.fishing: int = 0
        self.gold: int = 0
        self.drako: int = 0
        self.health: int = 0
        self.level: int = 0
        self.magic: int = 0
        self.max_health: int = 0
        self.stamina: int = 0
        self.sword: int = 0

    def __repr__(self):
        return f"Stats(bow={self.bow}, defence={self.defence}, fishing={self.fishing}, gold={self.gold}, health={self.health}, level={self.level}, magic={self.magic}, max_health={self.max_health}, stamina={self.stamina}, sword={self.sword})"


class Account:
    def __init__(self, config: AccountConfig):
        self.username: str = config.username
        self.password: str = config.password
        self.auto_equip: bool = config.auto_equip
        self.stats: Stats = Stats()
        self.mode: Mode = Mode.IDLE
        self.guild: Optional[str] = None
        self.hunt: Optional[Hunt] = None
        self.session: Client = httpx.Client(
            http2=False,
            timeout=httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=5.0),
            limits=httpx.Limits(
                max_connections=5,
                max_keepalive_connections=2,
                keepalive_expiry=15.0,
            ),
        )

    def __repr__(self):
        return f"Account(username='{self.username}', mode={self.mode}, guild={self.guild}, hunt={self.hunt})"
