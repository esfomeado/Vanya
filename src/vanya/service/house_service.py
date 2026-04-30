import json
import logging
import random
import re

from bs4 import BeautifulSoup

from src.vanya.core.constants import HOUSE_URL, HOUSE_CHANGE_OUTFIT_URL, HOUSE_BANK_URL, BASE_URL
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
                if item.get("filename") not in ("default_sprite.png", "knight.png")
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

    def generate_friend_code(self) -> str:
        logging.info(f"Generating house friend code for {self.account.username}")
        try:
            response = self.account.session.post(
                f"{BASE_URL}/process/house_friend_code.php",
                data={
                    "action": "generate"
                },
                headers={
                    "referer": HOUSE_URL,
                    "x-csrf-token": self.account.csrf,
                }
            )

            data = response.json()
            code = data.get("code", "")
            logging.info(f"Successfully generated friend code for {self.account.username}: {code}")
            return code

        except Exception as e:
            logging.error(f"Failed to generate house friend code for {self.account.username}: {e}")
            return ""

    def join_house(self, friend_code: str) -> None:
        logging.info(f"Attempting to join house with code {friend_code} for {self.account.username}")
        try:
            response = self.account.session.post(
                f"{BASE_URL}/process/house_friend_code.php",
                data={
                    "action": "join",
                    "code": friend_code
                },
                headers={
                    "referer": HOUSE_URL,
                    "x-csrf-token": self.account.csrf,
                }
            )

            data = response.json()
            logging.info(f"Join house response for {self.account.username}: {data}")

        except Exception as e:
            logging.error(f"Failed to join house for {self.account.username}: {e}")

    def withdraw_all_gold(self) -> None:
        logging.info(f"Checking banked gold for {self.account.username}")
        response = self.account.session.get(HOUSE_URL)
        soup = BeautifulSoup(response.text, "html.parser")

        bank_chip = soup.find("strong", id="banked-gold-chip")
        if not bank_chip:
            logging.warning(f"Banked gold chip not found for {self.account.username}")
            return

        banked_gold_str = bank_chip.get("data-raw-gold")
        if not banked_gold_str:
            banked_gold_str = bank_chip.get_text(strip=True).replace(",", "")

        try:
            banked_gold = int(banked_gold_str)
        except ValueError:
            logging.error(f"Failed to parse banked gold '{banked_gold_str}' for {self.account.username}")
            return

        if banked_gold <= 0:
            logging.info(f"No gold in bank for {self.account.username}")
            return

        logging.info(f"Withdrawing {banked_gold} gold for {self.account.username}")

        try:
            self.account.session.post(
                HOUSE_BANK_URL,
                data={
                    "action": "withdraw",
                    "amount": str(banked_gold)
                },
                headers={
                    "referer": HOUSE_URL,
                    "x-csrf-token": self.account.csrf,
                }
            )
            logging.info(f"Successfully withdrew {banked_gold} gold for {self.account.username}")
        except Exception as e:
            logging.error(f"Failed to withdraw gold for {self.account.username}: {e}")
