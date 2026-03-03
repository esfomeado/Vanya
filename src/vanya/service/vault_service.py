import logging

from src.vanya.core.constants import VAULT_URL
from src.vanya.model.account import Account


class VaultService:
    def __init__(self, account: Account):
        self.account = account

    def open_box(self, season: int) -> None:
        logging.info(f"Opening Vault Box for season {season} | account={self.account.username}")

        try:
            self.account.session.post(
                VAULT_URL,
                data={
                    "action": "open_box",
                    "box_id": f"gold_chest_season{season}",
                },
                headers={
                    "referer": VAULT_URL,
                },
            )
            logging.info(f"Successfully sent open box request for season {season}")
        except Exception as e:
            logging.error(f"Failed to open box for season {season}: {e}")
