import logging

from src.vanya.core.constants import GUILDS_URL, GUILDS_APPLY_URL, GUILDS_LEAVE_URL
from src.vanya.core.utils import get_global_csrf
from src.vanya.model.account import Account


class GuildService:
    def __init__(self, account: Account):
        self.account = account

    def join(self, guild_id: int) -> None:
        logging.info(
            f"Applying to guild {guild_id} | account={self.account.username}"
        )

        response = self.account.session.get(GUILDS_URL)
        response.raise_for_status()

        csrf = get_global_csrf(response.text)

        self.account.session.post(
            GUILDS_APPLY_URL,
            headers={
                "referer": GUILDS_URL,
                "x-csrf-token": csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
            data={
                "guild_id": guild_id,
            },
        ).raise_for_status()

    def leave(self, guild_id: int) -> None:
        logging.info(f"Leaving guild {guild_id} | account={self.account.username}")

        response = self.account.session.get(GUILDS_URL)
        response.raise_for_status()

        csrf = get_global_csrf(response.text)

        self.account.session.post(
            GUILDS_LEAVE_URL,
            headers={
                "referer": GUILDS_URL,
                "x-csrf-token": csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
            data={
                "guild_id": guild_id,
            }
        )
