import logging
import re
from typing import Optional

from src.vanya.core.constants import TRAIN_URL, PUB_URL, PUB_NPC_BUY_URL
from src.vanya.model.account import Account


class PubService:
    _instances: dict[str, "PubService"] = {}

    def __new__(cls, account: Account):
        if account.username not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[account.username] = instance
            instance._initialized = False
        return cls._instances[account.username]

    def __init__(self, account: Account):
        if self._initialized:
            return

        self.account = account
        self.csrf: Optional[str] = None
        self._initialized = True

    def go_to_pub(self):
        logging.info(f"Going to pub for account {self.account.username}")

        response = self.account.session.get(PUB_URL, timeout=10)
        self.csrf = self._get_csrf(response.text)

        self._stop_training()
        self._buy_health_potion()
        self._start_training()

    def _get_csrf(self, html: str):
        match = re.search(r'globalCsrfToken\s*=\s*"([a-f0-9]+)"', html)

        if not match:
            raise RuntimeError("CSRF token not found in PUB")
        return match.group(1)

    def _start_training(self):
        logging.info(f"Starting training for account {self.account.username}")

        self.account.session.post(
            TRAIN_URL,
            data={"action": "start"},
            headers={
                "origin": "https://vanyaonline.com",
                "referer": PUB_URL,
                "x-csrf-token": self.csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        ).raise_for_status()

    def _stop_training(self):
        logging.info(f"Stopping training for account {self.account.username}")

        self.account.session.post(
            TRAIN_URL,
            data={
                "action": "stop"
            },
            headers={
                "origin": "https://vanyaonline.com",
                "referer": PUB_URL,
                "x-csrf-token": self.csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        ).raise_for_status()

    def _buy_health_potion(self):
        logging.info(f"Buying health potion for account {self.account.username}")

        self.account.session.post(
            PUB_NPC_BUY_URL,
            data={
                "item_id": "3"
            },
            headers={
                "origin": "https://vanyaonline.com",
                "referer": PUB_URL,
                "x-csrf-token": self.csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        ).raise_for_status()
