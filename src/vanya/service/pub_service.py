import logging
from typing import Optional

from src.vanya.core.constants import TRAIN_URL, PUB_URL, PUB_NPC_BUY_URL
from src.vanya.core.utils import get_global_csrf
from src.vanya.model.account import Account


class PubService:
    def __init__(self, account: Account):
        self.account = account
        self.csrf: Optional[str] = None

    def go_to_pub(self) -> None:
        logging.info(f"Going to pub for account {self.account.username}")

        response = self.account.session.get(PUB_URL, timeout=10)
        self.csrf = get_global_csrf(response.text)

    def go_to_pub_and_heal(self) -> None:
        logging.info(f"Going to pub and healing for account {self.account.username}")

        self.go_to_pub()

        self._stop_training()
        self._buy_health_potion()
        self._start_training()

    def _start_training(self) -> None:
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

    def _stop_training(self) -> None:
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

    def _buy_health_potion(self) -> None:
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
