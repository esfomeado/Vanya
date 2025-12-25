import logging
import time

from bs4 import BeautifulSoup

from src.vanya.core.constants import DUNGEON_VIEW_URL, DUNGEON_LOBBY_URL
from src.vanya.model.account import Account
from src.vanya.model.hunt import Hunt
from src.vanya.service.base_hunt_service import BaseHuntService


class PhantomHallsService(BaseHuntService):
    _instances: dict[str, "PhantomHallsService"] = {}

    def __new__(cls, account: Account):
        if account.username not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[account.username] = instance
            instance._initialized = False
        return cls._instances[account.username]

    def __init__(self, account: Account):
        if self._initialized:
            return

        super().__init__(account)
        self._initialized = True

    def _join_dungeon_queue(self, dungeon_id: str):
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

    def _start_dungeon(self, dungeon_id: str):
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

    def _fetch_dungeon_lobby(self):
        return self.account.session.get(
            DUNGEON_LOBBY_URL,
            params={
                "ajax_lobby_status": "1",
                "_": int(time.time() * 1000),
            },
            headers={"referer": DUNGEON_VIEW_URL},
            timeout=10,
        ).json()

    def _get_latest_enabled_dungeon(self):
        resp = self.account.session.get(DUNGEON_VIEW_URL, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        dungeon_areas = soup.select(".hunt-area")

        if not dungeon_areas:
            return None, None, None

        for area in reversed(dungeon_areas):
            form = area.find("form", action="hunt_start")
            if not form:
                continue
            button = form.find("button", type="submit")
            if not button:
                continue
            if button.has_attr("disabled") or "disabled" in button.get("class", []):
                continue

            area_id = form.find("input", {"name": "area_id"}).get("value")
            # extract max_hit like in solo hunt
            dmg_span = area.select_one(".stat-row.damage-row span[title*='Expected damage']")
            max_hit = None
            if dmg_span:
                text = dmg_span.text.strip()
                max_hit = int(text.strip("()").split("-")[1].strip())
            return area, area_id, max_hit

        return None, None, None

    def hunt(self, area_id: str | None = None):
        joined = False

        while True:
            try:
                if not area_id:
                    _, area_id, max_hit = self._get_latest_enabled_dungeon()
                    if not area_id:
                        logging.warning("No enabled dungeon found for your level")
                        time.sleep(5)
                        continue
                else:
                    # if specific area_id, fetch max_hit from HTML
                    _, _, max_hit = self._get_latest_enabled_dungeon()  # you could make a variant that takes area_id

                if not self.account.hunt:
                    self.account.hunt = Hunt(area_id=area_id, name="Phantom Halls", max_hit=max_hit)

                if not joined:
                    self._join_dungeon_queue(area_id)
                    joined = True
                    time.sleep(5)
                    continue

                dungeon_status = self._fetch_dungeon_lobby().get(area_id)
                if not dungeon_status:
                    logging.warning(f"Dungeon {area_id} not in lobby yet")
                    time.sleep(5)
                    continue

                count = dungeon_status.get("count", 0)
                required_count = dungeon_status.get("required_count", 3)
                am_i_in = dungeon_status.get("am_i_in", False)

                if joined and not am_i_in:
                    return

                if count < required_count:
                    time.sleep(5)
                    continue

                self._start_dungeon(area_id)
                return

            except Exception as e:
                logging.error(f"Error while running dungeon hunt: {e}")
                time.sleep(5)
