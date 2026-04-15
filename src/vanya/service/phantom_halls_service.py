import logging
import time
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import DUNGEON_VIEW_URL
from src.vanya.model.account import Account
from src.vanya.model.hunt import Hunt
from src.vanya.model.mode import Mode
from src.vanya.service.base_hunt_service import BaseHuntService


class PhantomHallsService(BaseHuntService):
    def __init__(self, account: Account):
        super().__init__(account)

    def _start_dungeon(self, dungeon_id: str, pay_mode: str) -> None:
        self.account.session.post(
            DUNGEON_VIEW_URL,
            data={
                "area_id": dungeon_id,
                "dungeon_action": "skip",
                "pay_mode": pay_mode,
                "csrf_token": self.account.csrf
            },
            headers={
                "referer": DUNGEON_VIEW_URL
            },
        )

        logging.info(f"Started Phantom Halls {dungeon_id} using {pay_mode} for account {self.account.username}")

    def _get_latest_enabled_dungeon(self, specific_area_id: Optional[str] = None):
        response = self.account.session.get(DUNGEON_VIEW_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        dungeon_areas = soup.select(".hunt-area")

        if not dungeon_areas:
            logging.info(f"No dungeons found, attempting to claim daily tickets for {self.account.username}")
            self.account.session.post(
                DUNGEON_VIEW_URL,
                data={
                    "csrf_token": self.account.csrf,
                    "claim_phantom_daily_tickets": "1"
                },
                headers={
                    "referer": DUNGEON_VIEW_URL
                }
            )

            response = self.account.session.get(DUNGEON_VIEW_URL)
            soup = BeautifulSoup(response.text, "html.parser")
            dungeon_areas = soup.select(".hunt-area")

            if not dungeon_areas:
                return None, None, None, 0

        tickets = 0
        ticket_text = soup.find(string=lambda text: text and "Phantom Tickets:" in text)
        if ticket_text:
            try:
                parent = ticket_text.parent
                val_span = parent.find("span")
                if val_span:
                    tickets = int(val_span.text.strip())
            except Exception as e:
                logging.debug(f"Failed to parse tickets: {e}")

        for area in reversed(dungeon_areas):
            forms = area.find_all("form")
            form = None
            for f in forms:
                if f.find("input", {"name": "dungeon_action"}):
                    form = f
                    break

            if not form:
                continue

            area_id = form.find("input", {"name": "area_id"}).get("value")
            if specific_area_id and area_id != specific_area_id:
                continue

            button = form.find("button", type="submit")
            if not button or "HUNT" not in button.text.upper():
                continue

            dmg_span = area.select_one(".stat-row.damage-row span[title*='Expected damage']")
            max_hit = None
            if dmg_span:
                text = dmg_span.text.strip()
                max_hit = int(text.strip("()").split("-")[1].strip())

            return area, area_id, max_hit, tickets

        return None, None, None, tickets

    def hunt(self, specific_area_id: Optional[str] = None) -> None:
        self.last_hunt_start_time = time.time()
        self.area_id = specific_area_id

        _, area_id, max_hit, tickets = self._get_latest_enabled_dungeon(specific_area_id=specific_area_id)

        if not area_id:
            logging.info(f"No available dungeon found for {self.account.username}")
            return

        pay_mode = "ticket" if tickets > 0 else "stamina"

        self._start_dungeon(area_id, pay_mode)

        self.account.hunt = Hunt(area_id=area_id, name=area_id, max_hit=max_hit)
        self.account.mode = Mode.PHANTOM_HALLS
        logging.info(f"Joined Phantom Halls dungeon {area_id} for account {self.account.username}")
