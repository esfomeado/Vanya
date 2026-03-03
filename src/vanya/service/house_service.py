import json
import logging
import random
import re

from src.vanya.core.constants import HOUSE_URL, HOUSE_CHANGE_OUTFIT_URL
from src.vanya.model.account import Account
from src.vanya.model.outfit import Outfit


class HouseService:
    def __init__(self, account: Account):
        self.account = account

    def list_outfits(self) -> list[Outfit]:
        logging.info(f"Listing outfits for account {self.account.username}")

        response = self.account.session.get(HOUSE_URL)

        pattern = r"const PLAYER_OUTFITS = JSON\.parse\('(.+?)'\);"
        match = re.search(pattern, response.text)

        if not match:
            logging.warning(f"PLAYER_OUTFITS json not found for {self.account.username}")
            return []

        json_str = match.group(1)

        try:
            data = json.loads(json_str)
            return [
                Outfit(name=item.get("name"), filename=item.get("filename"))
                for item in data
            ]
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode outfits JSON for {self.account.username}: {e}")
            return []

    def equip_random_outfit(self) -> None:
        outfits = self.list_outfits()
        if not outfits:
            logging.warning(f"No outfits found for {self.account.username}")
            return

        outfit = random.choice(outfits)
        self.change_outfit(outfit.filename)

    def change_outfit(self, filename: str) -> None:
        logging.info(f"Changing outfit to {filename} for {self.account.username}")
        try:
            self.account.session.post(
                HOUSE_CHANGE_OUTFIT_URL,
                data={"outfit_file": filename},
                headers={
                    "referer": HOUSE_URL,
                    "x-csrf-token": self.account.csrf,
                },
            )
            logging.info(f"Successfully changed outfit to {filename}")
        except Exception as e:
            logging.error(f"Failed to change outfit to {filename}: {e}")
