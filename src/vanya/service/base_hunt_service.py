import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import STOP_HUNT_URL, BASE_URL, HUNT_URL
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.auto_equip_service import AutoEquipService
from src.vanya.service.boss_service import BossService
from src.vanya.service.nexus_service import NexusService
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry


class BaseHuntService(ABC):
    def __init__(self, account: Account):
        self.account = account
        self.area_id: Optional[str] = None
        self.last_chest_claim_time: float = 0
        self.auto_equip_service = service_registry.get(AutoEquipService, account)
        self.boss_service = service_registry.get(BossService, account)
        self.pub_service = service_registry.get(PubService, account)
        self.nexus_service = service_registry.get(NexusService, account)

    @abstractmethod
    def hunt(self, specific_area_id: Optional[str] = None) -> None:
        pass

    def stop_hunt(self) -> None:
        logging.info(f"Stopping hunt for account {self.account.username}")

        response = self.account.session.get(HUNT_URL)
        csrf = self._get_csrf(response.text)

        self.account.session.post(
            STOP_HUNT_URL,
            data={
                "action": "stop_hunt",
                "csrf_token": csrf
            },
            headers={
                "referer": BASE_URL
            },
        )

        self.account.hunt = None
        self.account.mode = Mode.IDLE

    def claim_chest(self) -> None:
        try:
            logging.info(f"Attempting to claim hunt chest for {self.account.username}")

            response_get = self.account.session.get(HUNT_URL)
            csrf = self._get_csrf(response_get.text)

            if not csrf:
                logging.warning("Could not find CSRF token for chest claim.")
                return

            self.account.session.post(
                HUNT_URL,
                data={
                    "action": "claim_hunt_chest",
                    "csrf_token": csrf
                },
                headers={
                    "referer": HUNT_URL,
                },
            )

            self.last_chest_claim_time = time.time()
            logging.info(f"Successfully sent chest claim request for {self.account.username}")

        except Exception as e:
            logging.error(f"Failed to claim chest: {e}")

    def tick(self) -> None:
        self.account.session.get(HUNT_URL)

        if time.time() - self.last_chest_claim_time > 1800:
            self.claim_chest()

        if self.account.stats.health <= self.account.hunt.max_hit + (self.account.hunt.max_hit * 0.1):
            logging.info(f"Health below max hit for account {self.account.username}, stopping hunt")
            self.stop_hunt()
            self.pub_service.go_to_pub_and_heal()
            self.pub_service.regenerate(sleep=False)
            self.auto_equip_service.equip()
            self.hunt(specific_area_id=self.area_id)

    def _get_csrf(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")

        for inp in soup.find_all("input"):
            if inp.get("name") == "csrf_token":
                return inp.get("value")

        return None
