import logging
import random
from typing import Optional

from curl_cffi import requests, Session

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
        self.hashed_accounts: int = 0

    def __repr__(self):
        return f"Stats(bow={self.bow}, defence={self.defence}, fishing={self.fishing}, gold={self.gold}, health={self.health}, level={self.level}, magic={self.magic}, max_health={self.max_health}, stamina={self.stamina}, sword={self.sword})"


class Account:
    def __init__(self, config: AccountConfig):
        self.username: str = config.username
        self.password: str = config.password
        self.auto_equip: bool = config.auto_equip
        self.boss_farm: bool = config.boss_farm
        self.stats: Stats = Stats()
        self.mode: Mode = Mode.IDLE
        self.guild: Optional[str] = None
        self.hunt: Optional[Hunt] = None
        self.session: Session = self._create_session(config)

    @staticmethod
    def _create_session(config: AccountConfig) -> Session:
        impersonations = [
            "chrome100",
            "chrome101",
            "chrome104",
            "chrome107",
            "chrome110",
            "chrome116",
            "chrome119",
            "chrome120",
            "chrome123",
            "chrome124",
            "chrome131",
            "chrome136",
            "chrome142",
        ]

        session = requests.Session(
            impersonate=random.choice(impersonations),
            timeout=5,
            raise_for_status=True,
        )

        session.headers.update({
            "accept": "text/html,application/xhtml+xml",
            "accept-language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })

        if config.proxy:
            formatted_proxy = Account._format_proxy(config.proxy)
            session.proxies.update({
                "http": formatted_proxy,
                "https": formatted_proxy,
            })
            logging.info(f"{config.username} initialized with proxy.")
        else:
            logging.info(f"{config.username} initialized using current IP (Direct).")

        return session

    @staticmethod
    def _format_proxy(proxy_str: str) -> str:
        parts = proxy_str.split(":")
        if len(parts) == 4:
            ip, port, user, password = parts
            return f"http://{user}:{password}@{ip}:{port}"

        if "://" not in proxy_str:
            return f"http://{proxy_str}"

        return proxy_str

    def __repr__(self):
        return f"Account(username='{self.username}', mode={self.mode}, guild={self.guild}, hunt={self.hunt})"
