import logging
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import CHECK_HUNT_STATUS_URL, HUNT_URL
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.phantom_halls_service import PhantomHallsService
from src.vanya.service.service_registry import service_registry
from src.vanya.service.solo_hunt_service import SoloHuntService


class ReconciliationService:
    def __init__(self, account: Account):
        self.account = account

    def reconcile(self) -> None:
        try:
            response = self.account.session.get(CHECK_HUNT_STATUS_URL)
            in_hunt = response.json().get("in_hunt", False)

            if self.account.mode in {Mode.SOLO_HUNT, Mode.PHANTOM_HALLS} and not in_hunt:
                logging.info(f"Reconciled mode for {self.account.username}: stopped hunt")

                self.account.mode = Mode.IDLE
                self.account.hunt = None
                return

            if self.account.mode == Mode.IDLE and in_hunt:
                mode, area_id = self._get_current_hunt_info()

                service_map = {
                    Mode.SOLO_HUNT: SoloHuntService,
                    Mode.PHANTOM_HALLS: PhantomHallsService
                }

                service_class = service_map.get(mode)

                if service_class:
                    logging.info(f"Reconciled mode for {self.account.username}: started hunt in {mode.value}")

                    service = service_registry.get(service_class, self.account)
                    service.stop_hunt()
                    service.hunt(area_id)

        except Exception as e:
            logging.warning(f"Failed to reconcile mode for {self.account.username}: {e}")

    def _get_current_hunt_info(self) -> tuple[Optional[Mode], Optional[str]]:
        hunt_name_to_mode = {
            "Dark Forest": Mode.SOLO_HUNT,
            "Dead River": Mode.SOLO_HUNT,
            "Forgotten Caverns": Mode.SOLO_HUNT,
            "Dragon Peaks": Mode.SOLO_HUNT,
            "Ashen Wastelands": Mode.SOLO_HUNT,
            "Crimson Depths": Mode.SOLO_HUNT,
            "Celestial Ruins": Mode.SOLO_HUNT,
            "Eternal Void": Mode.SOLO_HUNT,
            "Abyssal Gate": Mode.SOLO_HUNT,
            "Demon Fortress": Mode.SOLO_HUNT,
            "Abyss of Vanya": Mode.SOLO_HUNT,
            "Shadow Throne": Mode.PHANTOM_HALLS,
            "Astral Nexus": Mode.PHANTOM_HALLS,
            "Demona Edge": Mode.PHANTOM_HALLS,
            "The Penumbula": Mode.PHANTOM_HALLS,
            "The Ossuary Lord": Mode.PHANTOM_HALLS,
            "Dead Inside": Mode.PHANTOM_HALLS,
        }

        try:
            response = self.account.session.get(HUNT_URL)
            soup = BeautifulSoup(response.text, "html.parser")
            h1 = soup.select_one(".hunt-container h1")

            if not h1:
                return None, None

            hunt_text = h1.get_text(strip=True)
            name = hunt_text.split("Hunting in ")[1].split("(")[0].strip() if "Hunting in " in hunt_text else hunt_text

            mode = hunt_name_to_mode.get(name, Mode.SOLO_HUNT)
            area_id = name.lower().replace(" ", "_")

            return mode, area_id

        except Exception as e:
            logging.warning(f"Failed to get current hunt info for {self.account.username}: {e}")
            return None, None
