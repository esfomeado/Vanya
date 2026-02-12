import logging
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import EXPLORE_URL, BASE_URL
from src.vanya.core.errors import VanyaError
from src.vanya.model.account import Account
from src.vanya.model.hunt import Hunt
from src.vanya.model.mode import Mode
from src.vanya.service.base_hunt_service import BaseHuntService


class SoloHuntService(BaseHuntService):
    def __init__(self, account: Account):
        super().__init__(account)

    def hunt(self, specific_area_id: Optional[str] = None) -> None:
        logging.info(f"Starting solo hunt for {self.account.username}")

        self.area_id = specific_area_id

        response = self.account.session.get(EXPLORE_URL)

        soup = BeautifulSoup(response.text, "html.parser")
        hunt_areas = soup.select(".hunt-area")
        if not hunt_areas:
            raise VanyaError("No solo hunt areas found")

        selected_area = None

        for area in reversed(hunt_areas):
            form = area.find("form", action="hunt_start")
            if not form:
                continue

            area_input = form.find("input", {"name": "area_id"})
            csrf_input = form.find("input", {"name": "csrf_token"})
            button = form.find("button", type="submit")

            if not area_input or not csrf_input or not button:
                continue

            if button.has_attr("disabled"):
                continue

            if specific_area_id:
                if area_input.get("value") != specific_area_id:
                    continue
                selected_area = area
                break

            selected_area = area
            break

        if not selected_area:
            raise VanyaError(
                f"No enabled hunt area found "
                f"(area_id={specific_area_id})"
            )

        name = selected_area.find("h2").text.strip()

        dmg_span = selected_area.select_one(
            ".stat-row.damage-row span[title*='Expected damage']"
        )
        if not dmg_span:
            raise VanyaError(f"Could not parse damage for {name}")

        max_hit = int(dmg_span.get_text(strip=True).strip("()").split("-")[1].strip())

        form = selected_area.find("form", action="hunt_start")
        area_id_value = form.find("input", {"name": "area_id"}).get("value")
        csrf_value = form.find("input", {"name": "csrf_token"}).get("value")

        hunt = Hunt(
            area_id=area_id_value,
            name=name,
            max_hit=max_hit,
        )

        self.account.hunt = hunt
        self.account.mode = Mode.SOLO_HUNT

        post_url = form.get("action")
        if not post_url.startswith("http"):
            post_url = f"{BASE_URL}/actions/{post_url.lstrip('/')}"

        self.account.session.post(
            post_url,
            data={
                "area_id": hunt.area_id,
                "csrf_token": csrf_value,
            },
            headers={
                "referer": EXPLORE_URL
            },
        )
