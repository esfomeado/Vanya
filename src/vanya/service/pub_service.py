import logging
import re
import time

from src.vanya.core.constants import PUB_URL, PUB_NPC_BUY_URL, PUB_REGENERATE_URL, PUB_UPDATE_URL, \
    PUB_OFFLINE_TRAIN_URL, BUY_ACCUMULATED_URL, PUB_SAVE_FLAG_URL
from src.vanya.model.account import Account


class PubService:
    def __init__(self, account: Account):
        self.account = account

    def go_to_pub(self) -> str:
        logging.info(f"Going to pub for account {self.account.username}")

        response = self.account.session.get(PUB_URL)
        return response.text

    def go_to_pub_and_heal(self) -> None:
        logging.info(f"Going to pub and healing for account {self.account.username}")

        self.go_to_pub()

        self.stop_training()
        self.buy_health_potion()
        self._start_training()

    def regenerate(self, sleep: bool = True) -> None:
        html = self.go_to_pub()

        token_match = re.search(r"const PUB_REGEN_TOKEN\s*=\s*'([^']+)'", html)
        regen_token = token_match.group(1) if token_match else ""

        self.account.session.post(
            PUB_UPDATE_URL,
            data={
                "x": "100",
                "y": "100",
            },
            headers={
                "referer": PUB_URL,
                "x-csrf-token": self.account.csrf,
            },
        )

        self.account.session.post(
            PUB_REGENERATE_URL,
            headers={
                "referer": PUB_URL,
                "x-pub-regen": regen_token,
            },
        )

        if sleep:
            time.sleep(125)

    def buy_accumulated_regen(self):
        self.account.session.post(
            BUY_ACCUMULATED_URL,
            data={
                "currency": "gold",
            },
            headers={
                "referer": PUB_URL,
            },
        )

    def _start_training(self) -> None:
        logging.info(f"Starting training for account {self.account.username}")

        self.account.session.post(
            PUB_OFFLINE_TRAIN_URL,
            data={
                "action": "start"
            },
            headers={
                "referer": PUB_URL,
                "x-csrf-token": self.account.csrf,
            },
        )

    def stop_training(self) -> None:
        logging.info(f"Stopping training for account {self.account.username}")

        self.account.session.post(
            PUB_OFFLINE_TRAIN_URL,
            data={
                "action": "stop"
            },
            headers={
                "referer": PUB_URL,
                "x-csrf-token": self.account.csrf,
            },
        )

    def buy_health_potion(self) -> None:
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
                "referer": PUB_URL,
                "x-csrf-token": self.account.csrf,
            },
        )

    def _get_health_potion_price(self) -> int:
        response = self.account.session.get(PUB_URL)
        html = response.text

        match = re.search(
            r"name\s*:\s*['\"]Full Life Potion['\"][\s\S]*?cost\s*:\s*['\"]([^'\"]+)['\"]",
            html,
            re.IGNORECASE
        )

        if not match:
            logging.warning(f"Could not find health potion price for account {self.account.username}")
            return 20000

        digits = "".join(filter(str.isdigit, match.group(1)))
        return int(digits) if digits else 20000

    def change_flag(self, flag: str) -> None:
        self.account.session.post(
            PUB_SAVE_FLAG_URL,
            data={
                "country_flag": flag
            },
            headers={
                "referer": PUB_URL,
                "x-csrf-token": self.account.csrf,
            },
        )
