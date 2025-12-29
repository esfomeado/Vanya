import logging
import threading
import time

from src.vanya.core.errors import VanyaError
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.boss_service import BossService
from src.vanya.service.daily_tasks_service import DailyTasksService
from src.vanya.service.deep_dragon_service import DeepDragonService
from src.vanya.service.login_service import LoginService
from src.vanya.service.phantom_halls_service import PhantomHallsService
from src.vanya.service.service_registry import service_registry
from src.vanya.service.solo_hunt_service import SoloHuntService
from src.vanya.service.stats_service import StatsService
from src.vanya.service.training_service import TrainingService
from src.vanya.telegram.telegram_service import TelegramService


class Scheduler:
    MODE_TICK_INTERVAL = {
        Mode.BOSSES: 5,
        Mode.IDLE: 60,
        Mode.TRAINING: 1,
        Mode.SOLO_HUNT: 30,
        Mode.PHANTOM_HALLS: 30,
        Mode.DEEP_DRAGON: 30,
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
            thread.join(timeout=5)

        logging.info("Scheduler stopped.")

    def _run(self, account: Account):
        last_login_check = 0.0
        last_stats_refresh = 0.0

        while not self._stop_event.is_set():
            try:
                now = time.time()

                if now - last_login_check > 60.0:
                    login_service = service_registry.get(LoginService, account)
                    login_service.ensure_logged_in()
                    login_service.reconcile_mode()
                    last_login_check = now

                if now - last_stats_refresh > 30.0:
                    service_registry.get(StatsService, account).refresh_account_stats()
                    last_stats_refresh = now

                if account.mode == Mode.SOLO_HUNT:
                    service_registry.get(SoloHuntService, account).tick()

                    if account.stats.level >= 300:
                        service_registry.get(SoloHuntService, account).stop_hunt()
                        service_registry.get(PhantomHallsService, account).hunt()

                if account.mode == Mode.PHANTOM_HALLS:
                    service_registry.get(PhantomHallsService, account).tick()

                if account.mode == Mode.DEEP_DRAGON:
                    service_registry.get(DeepDragonService, account).tick()

                if account.mode == Mode.TRAINING:
                    service_registry.get(TrainingService, account).tick()

                if account.mode == Mode.BOSSES:
                    service_registry.get(BossService, account).tick()

                service_registry.get(DailyTasksService, account).run_if_due()

                self._stop_event.wait(self.MODE_TICK_INTERVAL[account.mode])
            except VanyaError as e:
                TelegramService().send(
                    f"❌ <b>Vanya error</b>\n"
                    f"<b>Account:</b> {account.username}\n"
                    f"<b>Error:</b> {type(e).__name__}\n"
                    f"<pre>{e}</pre>"
                )
            except:
                logging.exception("Unexpected error in scheduler thread.")
                time.sleep(5)
