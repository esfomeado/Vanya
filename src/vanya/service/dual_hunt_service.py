import logging
import time
from typing import Optional

from src.vanya.core.constants import DEEP_DRAGON_URL, HUNT_URL
from src.vanya.model.account import Account
from src.vanya.model.hunt import Hunt
from src.vanya.model.mode import Mode
from src.vanya.service.deep_dragon_service import DeepDragonService
from src.vanya.service.phantom_halls_service import PhantomHallsService
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry
from src.vanya.service.stats_service import StatsService


class DualHuntService:
    HUNT_DURATION = 3600

    def __init__(self, account: Account):
        self.account = account
        self.phantom_halls_service = service_registry.get(PhantomHallsService, account)
        self.deep_dragon_service = service_registry.get(DeepDragonService, account)
        self.pub_service = service_registry.get(PubService, account)
        self.stats_service = service_registry.get(StatsService, account)
        self.area_id: Optional[str] = None
        self.max_hit = 0
        self.last_hunt_start_time: float = 0
        self.last_chest_claim_time: float = 0
        self.last_hunt_health_check: float = 0

    def hunt(self, specific_area_id: Optional[str] = None) -> None:
        self.area_id = specific_area_id
        self.phantom_halls_service.hunt(specific_area_id=specific_area_id)
        self.max_hit = self.account.hunt.max_hit

        self.deep_dragon_service.hunt(duration=self.HUNT_DURATION, train=True)

        self.last_hunt_start_time = time.time()
        self.account.mode = Mode.DUAL_HUNT
        self.account.hunt = Hunt(area_id="dual_hunt", name="Dual Hunt", max_hit=self.max_hit)


    def tick(self) -> None:
        if time.time() - self.last_chest_claim_time > 1800:
            self.phantom_halls_service.claim_chest()
            self.last_chest_claim_time = time.time()

        if self.last_hunt_start_time > 0 and (time.time() - self.last_hunt_start_time >= (self.HUNT_DURATION + 10)):
            logging.info(f"Dual Hunt timer finished for {self.account.username}. Claiming and restarting.")

            self.phantom_halls_service.stop_hunt()
            self.deep_dragon_service.claim_rewards()
            self.pub_service.go_to_pub()
            self.pub_service.buy_health_potion()
            self.pub_service.regenerate(sleep=False)
            self.stats_service.refresh_account_stats()
            self.hunt(specific_area_id=self.area_id)
        else:
            self.account.session.get(
                f"{DEEP_DRAGON_URL}?ajax=live&csrf_token={self.account.csrf}",
                headers={
                    "referer": DEEP_DRAGON_URL,
                }
            )

            response = self.account.session.get(DEEP_DRAGON_URL)
            current_health, max_health = self.deep_dragon_service.parse_current_health(response.text)
            potion_count = self.deep_dragon_service.parse_potion_count(response.text)

            if time.time() - self.last_hunt_health_check > 60:
                response = self.account.session.get(HUNT_URL)
                hunt_health = self.phantom_halls_service.parse_current_health(response.text)
                current_health = int(min(current_health, hunt_health))
                self.last_hunt_health_check = time.time()

            if current_health == 0:
                logging.info(f"Dual Hunt health is 0 for {self.account.username}. Restarting.")

                self.account.session.get(HUNT_URL)
                self.phantom_halls_service.stop_hunt()
                self.account.session.get(DEEP_DRAGON_URL)
                self.pub_service.go_to_pub()
                self.pub_service.buy_health_potion()
                self.pub_service.regenerate(sleep=False)
                self.stats_service.refresh_account_stats()
                self.hunt(specific_area_id=self.area_id)
                return

            if 10 > potion_count > -1:
                logging.info(f"Potion count low ({potion_count}) for {self.account.username}. Buying more.")
                self.deep_dragon_service.buy_potions()

            if self.account.hunt.max_hit * 2.1 >= current_health > 0:
                logging.info(f"Low health ({current_health}) detected for {self.account.username}. Using potion.")
                self.deep_dragon_service.use_potion()

    def stop_hunt(self) -> None:
        self.phantom_halls_service.stop_hunt()
        self.deep_dragon_service.stop_hunt()

        self.max_hit = 0

        self.account.hunt = None
        self.account.mode = Mode.IDLE
