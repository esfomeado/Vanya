import datetime
import logging
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import CLAIM_REWARD_URL
from src.vanya.core.constants import DASHBOARD_URL, DEMON_PASS_URL, HUNTIARY_URL, UPDEX_URL, SEAL_ITEM_URL, BASE_URL, \
    BOOKS_OF_SHADOWS_URL, QUEST_COMPLETE_URL, GUILDS_URL, GUILD_SHRINE_SPIN_URL
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
        self._claim_shadow_book()
        self._spin_guild_shrine()
        self._claim_eventide()

        self._last_run = now.date()

    def _claim_daemon_pass_rewards(self) -> None:
        logging.info(f"Claiming daemon pass rewards for {self.account.username}")

        status = self.account.session.get(
            f"{BASE_URL}/actions/demon_pass",
            headers={
                "referer": DASHBOARD_URL,
            },
        )

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
                    "x-csrf-token": self.account.csrf,
                },
                data={
                    "action": "claim",
                    "tier": tier,
                },
            )

    def _claim_huntiary_rewards(self) -> None:
        logging.info(f"Claiming huntiary daily rewards for {self.account.username}")

        self.account.session.post(
            HUNTIARY_URL,
            data={
                "action_type": "claim_daily"
            },
            headers={
                "referer": HUNTIARY_URL,
            },
        )

    def _seal_updex_items(self) -> None:
        logging.info(f"Sealing updex items for {self.account.username}")

        response = self.account.session.get(UPDEX_URL)
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
                data={
                    "item_name": item_name
                },
                headers={
                    "referer": UPDEX_URL,
                    "x-csrf-token": self.account.csrf,
                },
            )

    def _claim_shadow_book(self) -> None:
        response = self.account.session.get(
            BOOKS_OF_SHADOWS_URL,
            headers={
                "referer": BOOKS_OF_SHADOWS_URL
            },
        )

        soup = BeautifulSoup(response.text, "html.parser")

        claim_links = soup.select(
            ".quest-book:not(.locked-seq) a.complete-btn[href*='quest_complete']"
        )

        if not claim_links:
            logging.info(
                f"No Shadow Book rewards ready for {self.account.username}"
            )
            return

        for link in claim_links:
            href = link.get("href")

            if not href:
                continue

            quest_id = href.split("quest_id=")[-1]

            logging.info(
                f"Claiming Shadow Book quest {quest_id} "
                f"for {self.account.username}"
            )

            self.account.session.get(
                QUEST_COMPLETE_URL,
                params={
                    "quest_id": quest_id
                },
                headers={
                    "referer": BOOKS_OF_SHADOWS_URL
                },
            )

    def _spin_guild_shrine(self) -> None:
        if not self.account.guild:
            logging.info(f"{self.account.username} not in guild, skipping guild shrine spin")
            return

        self.account.session.post(
            GUILD_SHRINE_SPIN_URL,
            headers={
                "referer": GUILDS_URL,
                "x-csrf-token": self.account.csrf,
            },
            data={
                "csrf_token": self.account.csrf,
            },
        )

        logging.info(f"Guild shrine spin executed for {self.account.username}")

    def _claim_eventide(self) -> None:
        logging.info(f"Claiming eventide for {self.account.username}")

        self.account.session.post(
            CLAIM_REWARD_URL,
            headers={
                "referer": f"{BASE_URL}/account_settings",
            },
        )
