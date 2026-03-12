import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import STOP_HUNT_URL, BASE_URL, HUNT_URL
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.auto_equip_service import AutoEquipService
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry
from src.vanya.service.stats_service import StatsService


class BaseHuntService(ABC):
    MAX_HUNT_DURATION = 36000

    def __init__(self, account: Account):
        self.account = account
        self.area_id: Optional[str] = None
        self.last_chest_claim_time: float = 0
        self.last_hunt_start_time: float = 0
        self.auto_equip_service = service_registry.get(AutoEquipService, account)
        self.pub_service = service_registry.get(PubService, account)
        self.stats_service = service_registry.get(StatsService, account)

    @abstractmethod
    def hunt(self, specific_area_id: Optional[str] = None) -> None:
        pass

    def stop_hunt(self) -> None:
        logging.info(f"Stopping hunt for account {self.account.username}")

        self.account.session.post(
            STOP_HUNT_URL,
            data={
                "action": "stop_hunt",
                "csrf_token": self.account.csrf
            },
            headers={
                "referer": BASE_URL
            },
        )

        self.account.mode = Mode.IDLE
        self.account.hunt = None

    def claim_chest(self) -> None:
        try:
            logging.info(f"Attempting to claim hunt chest for {self.account.username}")

            self.account.session.post(
                HUNT_URL,
                data={
                    "action": "claim_hunt_chest",
                    "csrf_token": self.account.csrf
                },
                headers={
                    "referer": HUNT_URL,
                },
            )

            self.last_chest_claim_time = time.time()
            logging.info(f"Successfully sent chest claim request for {self.account.username}")

        except Exception as e:
            logging.error(f"Failed to claim chest: {e}")

    def parse_current_health(self, html: str) -> int:
        soup = BeautifulSoup(html, "html.parser")
        life_span = soup.find("span", id="lifeSpan")
        if life_span:
            return int(life_span.get_text(strip=True).replace(",", ""))
        return self.account.stats.health

    def tick(self) -> None:
        self.account.session.get(HUNT_URL)

        if time.time() - self.last_chest_claim_time > 1800:
            self.claim_chest()

        if self.account.hunt and (self.account.stats.health <= (self.account.hunt.max_hit * 1.2) or (time.time() - self.last_hunt_start_time >= self.MAX_HUNT_DURATION)):
            logging.info(f"Health ({self.account.stats.health}) below max hit for account {self.account.username}, stopping hunt")
            self.stop_hunt()
            self.pub_service.go_to_pub_and_heal()
            self.pub_service.regenerate(sleep=False)
            self.auto_equip_service.equip()
            self.stats_service.refresh_account_stats()
            self.hunt(specific_area_id=self.area_id)
