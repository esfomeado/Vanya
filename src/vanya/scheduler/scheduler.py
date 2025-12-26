import logging
import threading
import time

from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.boss_service import BossService
from src.vanya.service.login_service import LoginService
from src.vanya.service.phantom_halls_service import PhantomHallsService
from src.vanya.service.service_registry import service_registry
from src.vanya.service.solo_hunt_service import SoloHuntService
from src.vanya.service.stats_service import StatsService
from src.vanya.service.training_service import TrainingService


class Scheduler:
    MODE_TICK_INTERVAL = {
        Mode.BOSSES: 5,
        Mode.IDLE: 60,
        Mode.TRAINING: 1,
        Mode.SOLO_HUNT: 60,
        Mode.PHANTOM_HALLS: 60,
        Mode.DEEP_DRAGON: 60,
    }

    def __init__(self, accounts: list[Account]):
        self.accounts = accounts
        self._threads = []
        self._stop_event = threading.Event()

    def start(self):
        for account in self.accounts:
            t = threading.Thread(target=self._run, args=(account,), daemon=True)
            t.start()
            self._threads.append(t)

        logging.info("Scheduler started for all accounts.")

    def stop(self):
        self._stop_event.set()
        for thread in self._threads:
            thread.join()

        logging.info("Scheduler stopped.")

    def _run(self, account: Account):
        last_login_check = 0.0

        while not self._stop_event.is_set():
            now: float = time.time()

            if now - last_login_check > 60:
                login_service = service_registry.get(LoginService, account)
                login_service.ensure_logged_in()
                login_service.reconcile_mode()

                service_registry.get(StatsService, account).refresh_account_stats()

                last_login_check = now

            if account.mode == Mode.SOLO_HUNT:
                service_registry.get(SoloHuntService, account).tick()

            if account.mode == Mode.PHANTOM_HALLS:
                service_registry.get(PhantomHallsService, account).tick()

            if account.mode == Mode.TRAINING:
                service_registry.get(TrainingService, account).tick()

            if account.mode == Mode.BOSSES:
                service_registry.get(BossService, account).tick()

            time.sleep(self.MODE_TICK_INTERVAL[account.mode])
