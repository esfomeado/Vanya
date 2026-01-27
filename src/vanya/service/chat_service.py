import logging
from typing import Optional

from src.vanya.core.constants import PUB_MURAL_POST_URL, PUB_URL, HUNT_URL
from src.vanya.core.utils import get_global_csrf
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode


class ChatService:
    CSRF_SOURCE_BY_MODE: dict[Mode, Optional[str]] = {
        Mode.BOSSES: None,
        Mode.IDLE: PUB_URL,
        Mode.TRAINING: PUB_URL,
        Mode.SOLO_HUNT: HUNT_URL,
        Mode.PHANTOM_HALLS: HUNT_URL,
        Mode.DEEP_DRAGON: HUNT_URL,
    }

    def __init__(self, account: Account):
        self.account = account

    def post_message(self, message: str, channel: str = "global") -> None:
        csrf = self._fetch_csrf()
        referer_url = self.CSRF_SOURCE_BY_MODE.get(
            self.account.mode,
            PUB_URL,
        )

        self.account.session.post(
            PUB_MURAL_POST_URL,
            data={
                "message": message,
                "channel": channel,
            },
            headers={
                "referer": referer_url,
                "x-csrf-token": csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
        ).raise_for_status()

        logging.info(
            "Chat message sent | account=%s | channel=%s",
            self.account.username,
            channel,
        )

    def _fetch_csrf(self) -> str:
        source_url = self.CSRF_SOURCE_BY_MODE.get(
            self.account.mode,
            PUB_URL,
        )

        response = self.account.session.get(source_url)
        response.raise_for_status()

        return get_global_csrf(response.text)
