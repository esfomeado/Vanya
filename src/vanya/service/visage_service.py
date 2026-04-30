import logging

from bs4 import BeautifulSoup

from src.vanya.core.constants import DASHBOARD_URL
from src.vanya.model.account import Account
from src.vanya.model.visage import Visage


class VisageService:
    def __init__(self, account: Account):
        self.account = account

    def list(self) -> list[Visage]:
        logging.info(f"Fetching owned visages for {self.account.username}")

        response = self.account.session.get(DASHBOARD_URL)

        soup = BeautifulSoup(response.text, "html.parser")
        visages: list[Visage] = []

        grid = soup.find("div", id="ownedPortraitsGrid")
        if not grid:
            logging.warning(f"Owned portraits grid not found for {self.account.username}")
            return []

        for card in grid.select(".portrait-card[data-owned='1']"):
            name_el = card.select_one(".portrait-name")
            name = name_el.get_text(strip=True) if name_el else "Unknown"

            bonus_el = card.select_one(".portrait-bonus")
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

        self.account.session.post(
            DASHBOARD_URL,
            data={
                "portrait_action": "equip",
                "csrf_token": self.account.csrf,
                "portrait": portrait_filename
            },
            headers={
                "referer": DASHBOARD_URL,
                "x-csrf-token": self.account.csrf,
            }
        )

        logging.info(f"Successfully equipped portrait '{portrait_filename}' for {self.account.username}")

    def spin(self) -> dict:
        logging.info(f"Spinning visage for {self.account.username}")

        response = self.account.session.post(
            DASHBOARD_URL,
            data={
                "portrait_action": "spin",
                "csrf_token": self.account.csrf,
                "currency": "gold"
            },
            headers={
                "referer": DASHBOARD_URL,
                "x-csrf-token": self.account.csrf,
            }
        )

        return response.json()

    def free_spin(self) -> None:
        logging.info(f"Free spinning visage for {self.account.username}")

        self.account.session.post(
            DASHBOARD_URL,
            data={
                "portrait_action": "spin_free",
                "csrf_token": self.account.csrf,
            },
            headers={
                "referer": DASHBOARD_URL,
                "x-csrf-token": self.account.csrf,
            }
        )
