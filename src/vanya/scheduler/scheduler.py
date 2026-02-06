import logging
import threading
import time

from requests import ConnectionError, HTTPError
from requests import ReadTimeout

from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.boss_service import BossService
from src.vanya.service.daily_tasks_service import DailyTasksService
from src.vanya.service.deep_dragon_service import DeepDragonService
from src.vanya.service.house_training_service import HouseTrainingService
from src.vanya.service.login_service import LoginService
from src.vanya.service.nexus_service import NexusService
from src.vanya.service.phantom_halls_service import PhantomHallsService
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry
from src.vanya.service.solo_hunt_service import SoloHuntService
from src.vanya.service.stats_service import StatsService
from src.vanya.service.training_service import TrainingService
from src.vanya.telegram.telegram_service import TelegramService


class Scheduler:
    MODE_TICK_INTERVAL = {
        Mode.BOSSES: 5,
        Mode.HOUSE_TRAINING: 0.5,
        Mode.IDLE: 60,
        Mode.TRAINING: 1,
        Mode.SOLO_HUNT: 25,
        Mode.PHANTOM_HALLS: 25,
        Mode.DEEP_DRAGON: 5,
    }

    def __init__(self, accounts: list[Account]):
        self.accounts: list[Account] = accounts
        self._threads: list[threading.Thread] = []
        self._stop_event: threading.Event = threading.Event()

    def start(self) -> None:
        for account in self.accounts:
            login_thread = threading.Thread(target=self._login_loop, args=(account,), daemon=True)
            login_thread.start()
            self._threads.append(login_thread)

            time.sleep(5)

            main_thread = threading.Thread(target=self._run, args=(account,), daemon=True)
            main_thread.start()
            self._threads.append(main_thread)

        logging.info("Scheduler started for all accounts.")

    def stop(self) -> None:
        self._stop_event.set()
        for thread in self._threads:
            thread.join(timeout=5)

        logging.info("Scheduler stopped.")

    def _login_loop(self, account: Account) -> None:
        login_service: LoginService = service_registry.get(LoginService, account)

        while not self._stop_event.is_set():
            login_service.ensure_logged_in()
            login_service.reconcile_mode()

            self._stop_event.wait(60)

    def _run(self, account: Account) -> None:
        last_stats_refresh = 0.0

        while not self._stop_event.is_set():
            try:
                now = time.time()

                if now - last_stats_refresh >= 20.0:
                    service_registry.get(StatsService, account).refresh_account_stats()
                    service_registry.get(NexusService, account).refresh()
                    last_stats_refresh = now

                if account.mode == Mode.SOLO_HUNT:
                    service_registry.get(SoloHuntService, account).tick()

                    if account.stats.level >= 300:
                        service_registry.get(SoloHuntService, account).stop_hunt()
                        service_registry.get(PhantomHallsService, account).hunt()

                if account.mode == Mode.PHANTOM_HALLS:
                    service_registry.get(PhantomHallsService, account).tick()
                    service_registry.get(NexusService, account).farm()

                if account.mode == Mode.DEEP_DRAGON:
                    service_registry.get(DeepDragonService, account).tick()

                if account.mode == Mode.TRAINING:
                    service_registry.get(TrainingService, account).tick()

                if account.mode == Mode.BOSSES:
                    service_registry.get(BossService, account).tick()

                if account.mode == Mode.HOUSE_TRAINING:
                    service_registry.get(HouseTrainingService, account).tick()

                if account.stats.health <= 1:
                    service_registry.get(PubService, account).go_to_pub_and_heal()

                service_registry.get(DailyTasksService, account).run_if_due()

                self._stop_event.wait(self.MODE_TICK_INTERVAL[account.mode])
            except (ConnectionError, ReadTimeout, HTTPError):
                pass
            except Exception as e:
                logging.exception("Unexpected error in scheduler thread.")

                TelegramService().send(
                    f"Account: {account.username}\n"
                    f"Error: {type(e).__name__}\n"
                    f"{e}"
                )

                time.sleep(5)
