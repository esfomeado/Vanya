import logging

from bs4 import BeautifulSoup

from src.vanya.core.constants import DASHBOARD_URL
from src.vanya.core.utils import get_global_csrf
from src.vanya.model.visage import Visage


class VisageService:
    def __init__(self, account):
        self.account = account

    def list(self) -> list[Visage]:
        logging.info(f"Fetching owned visages for {self.account.username}")

        response = self.account.session.get(DASHBOARD_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        visages: list[Visage] = []

        grid = soup.find("div", id="ownedPortraitsGrid")
        if not grid:
            logging.warning(f"Owned portraits grid not found for {self.account.username}")
            return []

        for card in grid.select(".portrait-card"):
            name_el = card.find("div", style=lambda s: s and "font-weight:800" in s)
            name = name_el.get_text(strip=True) if name_el else "Unknown"

            bonus_el = card.find("div", style=lambda s: s and "font-size:11px" in s)
            bonus = bonus_el.get_text(strip=True) if bonus_el else "No bonus"

            img_el = card.find("img")
            image_url = img_el.get("src") if img_el else ""

            button = card.select_one("button.portrait-equip-btn")
            is_equipped = False
            filename = ""

            if button:
                is_equipped = button.get("data-equipped") == "1"
                filename = button.get("data-portrait", "")

            visages.append(
                Visage(
                    name=name,
                    bonus=bonus,
                    image_url=image_url,
                    is_equipped=is_equipped,
                    filename=filename
                )
            )

        return visages

    def equip(self, portrait_filename: str) -> None:
        logging.info(f"Attempting to equip portrait '{portrait_filename}' for {self.account.username}")

        response = self.account.session.get(DASHBOARD_URL)
        response.raise_for_status()

        csrf = get_global_csrf(response.text)

        self.account.session.post(
            DASHBOARD_URL,
            data={
                "portrait_action": "equip",
                "csrf_token": csrf,
                "portrait": portrait_filename
            },
            headers={
                "referer": DASHBOARD_URL,
                "origin": "https://vanyaonline.com",
                "content-type": "application/x-www-form-urlencoded",
                "x-csrf-token": csrf,
            }
        ).raise_for_status()

        logging.info(f"Successfully equipped portrait '{portrait_filename}' for {self.account.username}")

    def spin(self):
        logging.info(f"Spinning visage for {self.account.username}")

        response = self.account.session.get(DASHBOARD_URL)
        response.raise_for_status()
        csrf = get_global_csrf(response.text)

        response = self.account.session.post(
            DASHBOARD_URL,
            data={
                "portrait_action": "spin",
                "csrf_token": csrf,
                "currency": "gold"
            },
            headers={
                "referer": DASHBOARD_URL,
                "origin": "https://vanyaonline.com",
                "content-type": "application/x-www-form-urlencoded",
                "x-csrf-token": csrf,
            }
        )

        response.raise_for_status()

        return response.json()
