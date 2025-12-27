import logging
from abc import ABC, abstractmethod
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import STOP_HUNT_URL, BASE_URL, HUNT_URL
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.auto_equip_service import AutoEquipService
from src.vanya.service.boss_service import BossService
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry


class BaseHuntService(ABC):
    def __init__(self, account: Account):
        self.account = account
        self.auto_equip_service = service_registry.get(AutoEquipService, account)
        self.boss_service = service_registry.get(BossService, account)
        self.pub_service = service_registry.get(PubService, account)

    @abstractmethod
    def hunt(self, area_id: Optional[str] = None) -> None:
        pass

    def stop_hunt(self) -> None:
        logging.info(f"Stopping hunt for account {self.account.username}")

        response = self.account.session.get(HUNT_URL, timeout=10)
        csrf = self._get_csrf(response.text)

        self.account.session.post(
            STOP_HUNT_URL,
            data={
                "action": "stop_hunt",
                "csrf_token": csrf
            },
            headers={"referer": BASE_URL},
            timeout=10,
        ).raise_for_status()

        self.account.hunt = None
        self.account.mode = Mode.IDLE

    def tick(self) -> None:
        if self.account.stats.health <= self.account.hunt.max_hit + 10:
            logging.info(f"Health below max hit for account {self.account.username}, stopping hunt")
            self.stop_hunt()
            self.pub_service.go_to_pub_and_heal()
            self.auto_equip_service.equip()
            self.hunt()

    def _get_csrf(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")

        for inp in soup.find_all("input"):
            if inp.get("name") == "csrf_token":
                return inp.get("value")

        return None
