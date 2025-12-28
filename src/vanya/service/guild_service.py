import logging

from src.vanya.core.constants import GUILDS_URL, GUILDS_APPLY_URL
from src.vanya.core.utils import get_global_csrf


class GuildService:
    def __init__(self, account):
        self.account = account

    def join(self, guild_id: int) -> None:
        logging.info(
            f"Applying to guild {guild_id} | account={self.account.username}"
        )

        response = self.account.session.get(GUILDS_URL, timeout=10)
        response.raise_for_status()

        csrf = get_global_csrf(response.text)

        self.account.session.post(
            GUILDS_APPLY_URL,
            headers={
                "origin": "https://vanyaonline.com",
                "referer": GUILDS_URL,
                "x-csrf-token": csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
            data={
                "guild_id": guild_id,
            },
            timeout=10,
        ).raise_for_status()
