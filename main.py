from src.vanya.core.config_loader import CONFIG
from src.vanya.core.logging_config import setup_logging
from src.vanya.model.account import Account
from src.vanya.scheduler.scheduler import Scheduler
from src.vanya.telegram.bot import start_telegram

if __name__ == "__main__":
    setup_logging()

    accounts: list[Account] = [Account(account_config) for account_config in CONFIG.accounts]

    scheduler = Scheduler(accounts)
    scheduler.start()

    start_telegram(accounts)
