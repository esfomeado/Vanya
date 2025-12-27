import logging
import re
import time
from typing import Optional

from src.vanya.core.constants import TRAIN_URL, PUB_URL, PUB_NPC_BUY_URL, PUB_REGENERATE_URL
from src.vanya.core.errors import VanyaError
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

    def regenerate(self) -> None:
        self.account.session.post(
            PUB_REGENERATE_URL,
            headers={
                "referer": PUB_URL,
            },
            timeout=10,
        ).raise_for_status()
        time.sleep(121)

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
        logging.info(f"Attempting to buy health potion for account {self.account.username}")

        health_potion_price = self._get_health_potion_price()

        if self.account.stats.gold < health_potion_price:
            logging.info(
                f"Not enough gold to buy potion for account {self.account.username}. "
                f"Needed: {health_potion_price}, Available: {self.account.stats.gold}. Regenerating..."
            )
            for _ in range(4):
                self.regenerate()

            return

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

    def _get_health_potion_price(self) -> int:
        response = self.account.session.get(PUB_URL, timeout=10)
        response.raise_for_status()
        html = response.text

        match = re.search(r'items\s*=\s*(\[[^]]*])', html)
        if not match:
            raise VanyaError("Failed to get items from pub page")

        items_js = match.group(1)

        potion_match = re.search(r'{[^}]*name\s*:\s*"Full Life Potion"[^}]*cost\s*:\s*"([^"]+)"', items_js)
        if not potion_match:
            raise VanyaError("Failed to get health potion price from pub page")

        cost_text = potion_match.group(1).replace(",", "").strip()
        digits = "".join(filter(str.isdigit, cost_text))
        return int(digits) if digits else 0
