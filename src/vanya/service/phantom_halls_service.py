import logging
import time
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import DUNGEON_VIEW_URL, DUNGEON_LOBBY_URL, CHECK_HUNT_STATUS_URL
from src.vanya.model.account import Account
from src.vanya.model.hunt import Hunt
from src.vanya.model.mode import Mode
from src.vanya.service.base_hunt_service import BaseHuntService


class PhantomHallsService(BaseHuntService):
    def __init__(self, account: Account):
        super().__init__(account)

    def _join_dungeon_queue(self, dungeon_id: str) -> None:
        self.account.session.post(
            DUNGEON_VIEW_URL,
            data={
                "area_id": dungeon_id,
                "dungeon_action": "join",
            },
            headers={"referer": DUNGEON_VIEW_URL},
            timeout=10,
        ).raise_for_status()

        logging.info(f"Joined dungeon {dungeon_id} queue for account {self.account.username}")

    def _start_dungeon(self, dungeon_id: str) -> None:
        self.account.session.post(
            DUNGEON_VIEW_URL,
            data={
                "area_id": dungeon_id,
                "dungeon_action": "start",
            },
            headers={"referer": DUNGEON_VIEW_URL},
            timeout=10,
        ).raise_for_status()

        logging.info(f"Started dungeon {dungeon_id} for account {self.account.username}")

    def _fetch_dungeon_lobby(self) -> dict:
        return self.account.session.get(
            DUNGEON_LOBBY_URL,
            params={
                "ajax_lobby_status": "1",
                "_": int(time.time() * 1000),
            },
            headers={"referer": DUNGEON_VIEW_URL},
            timeout=10,
        ).json()

    def _get_latest_enabled_dungeon(self, specific_area_id: Optional[str] = None):
        response = self.account.session.get(DUNGEON_VIEW_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        dungeon_areas = soup.select(".hunt-area")

        if not dungeon_areas:
            return None, None, None, None, None

        for area in reversed(dungeon_areas):
            form = area.find("form")
            if not form:
                continue

            area_id = form.find("input", {"name": "area_id"}).get("value")
            if specific_area_id and area_id != specific_area_id:
                continue

            button = form.find("button", type="submit")
            if not button or ("QUEUE UP" not in button.text and "Leave" not in button.text):
                continue

            dmg_span = area.select_one(".stat-row.damage-row span[title*='Expected damage']")
            max_hit = None
            if dmg_span:
                text = dmg_span.text.strip()
                max_hit = int(text.strip("()").split("-")[1].strip())

            lobby_span = area.select_one(f"span#lobby-count-{area_id}")
            count, required_count = 0, 0
            if lobby_span:
                text = lobby_span.text.strip()
                if "/" in text:
                    count_str, req_str = text.split("/")
                    count, required_count = int(count_str.strip()), int(req_str.strip())

            return area, area_id, max_hit, count, required_count

        return None, None, None, None, None

    def hunt(self, area_id: Optional[str] = None) -> None:
        self.area_id = area_id
        joined = False

        if not area_id:
            _, area_id, max_hit, count, required_count = self._get_latest_enabled_dungeon()
        if not area_id:
            return
        else:
            _, area_id, max_hit, count, required_count = self._get_latest_enabled_dungeon(
                specific_area_id=area_id)

        while True:
            try:
                if not joined:
                    self._join_dungeon_queue(area_id)
                    joined = True
                    time.sleep(3)
                    continue

                dungeon_status = self._fetch_dungeon_lobby().get(area_id)

                count = dungeon_status.get("count", 0)
                am_i_in = dungeon_status.get("am_i_in", False)

                if joined and not am_i_in:
                    response = self.account.session.get(
                        CHECK_HUNT_STATUS_URL,
                        timeout=10,
                    )
                    response.raise_for_status()
                    in_hunt = response.json().get("in_hunt", False)

                    if in_hunt:
                        self.account.hunt = Hunt(area_id=area_id, name=area_id, max_hit=max_hit)
                        self.account.mode = Mode.PHANTOM_HALLS

                        logging.info(f"Joined dungeon {area_id} for account {self.account.username}")
                        return

                    joined = False
                    time.sleep(5)

                if count < required_count:
                    time.sleep(3)
                    continue

                self._start_dungeon(area_id)
                self.account.hunt = Hunt(area_id=area_id, name=area_id, max_hit=max_hit)
                self.account.mode = Mode.PHANTOM_HALLS
                logging.info(f"Joined dungeon {area_id} for account {self.account.username}")

                return
            except Exception as e:
                logging.error(f"Error while running dungeon hunt: {e}")
                time.sleep(10)
