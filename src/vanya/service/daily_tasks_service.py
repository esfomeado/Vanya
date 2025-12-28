import datetime
import logging
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import DASHBOARD_URL, DEMON_PASS_URL, HUNTIARY_URL, UPDEX_URL, SEAL_ITEM_URL, BASE_URL
from src.vanya.core.utils import get_global_csrf
from src.vanya.model.account import Account


class DailyTasksService:
    def __init__(self, account: Account):
        self.account = account
        self._last_run: Optional[datetime.date] = None

    def run_if_due(self) -> None:
        now = datetime.datetime.now()
        if now.hour != 21:
            return

        if self._last_run == now.date():
            return

        self._claim_daemon_pass_rewards()
        self._claim_huntiary_rewards()
        self._seal_updex_items()

        self._last_run = now.date()

    def _claim_daemon_pass_rewards(self) -> None:
        logging.info(f"Claiming daemon pass rewards for {self.account.username}")

        response = self.account.session.get(DASHBOARD_URL, timeout=10)
        response.raise_for_status()
        csrf = get_global_csrf(response.text)

        status = self.account.session.get(
            f"{BASE_URL}/actions/demon_pass",
            headers={
                "referer": DASHBOARD_URL,
                "accept": "*/*",
            },
            timeout=10,
        )
        status.raise_for_status()

        data = status.json()

        current_day = int(data["current_day"])
        claimed: set[int] = set(data["pass"]["claimed"])
        max_tier = min(current_day, 5)

        for tier in range(1, max_tier + 1):
            if tier in claimed:
                continue

            logging.info(
                f"Claiming daemon pass tier {tier} for {self.account.username}"
            )

            self.account.session.post(
                DEMON_PASS_URL,
                headers={
                    "referer": DASHBOARD_URL,
                    "origin": "https://vanyaonline.com",
                    "x-csrf-token": csrf,
                    "content-type": "application/x-www-form-urlencoded",
                },
                data={
                    "action": "claim",
                    "tier": tier,
                },
                timeout=10,
            ).raise_for_status()

    def _claim_huntiary_rewards(self) -> None:
        logging.info(f"Claiming huntiary daily rewards for {self.account.username}")

        response = self.account.session.post(
            HUNTIARY_URL,
            data={"action_type": "claim_daily"},
            headers={
                "origin": "https://vanyaonline.com",
                "referer": HUNTIARY_URL,
                "content-type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        )
        response.raise_for_status()

    def _seal_updex_items(self) -> None:
        logging.info(f"Sealing updex items for {self.account.username}")

        response = self.account.session.get(UPDEX_URL, timeout=10)
        response.raise_for_status()

        self.csrf = get_global_csrf(response.text)
        soup = BeautifulSoup(response.text, "html.parser")

        for btn in soup.select("button.seal-btn.primary"):
            parent = btn.find_parent("div", class_="inv-card")
            item_name_el = parent.select_one(".inv-name")
            if not item_name_el:
                continue

            item_name = item_name_el.text.strip()
            logging.info(f"Sealing item: {item_name}")

            self.account.session.post(
                SEAL_ITEM_URL,
                data={"item_name": item_name},
                headers={
                    "referer": UPDEX_URL,
                    "origin": "https://vanyaonline.com",
                    "x-csrf-token": self.csrf,
                    "content-type": "application/x-www-form-urlencoded",
                },
                timeout=10,
            ).raise_for_status()
