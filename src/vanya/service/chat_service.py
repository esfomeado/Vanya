import logging
import re

from src.vanya.core.constants import PUB_MURAL_POST_URL, BASE_URL, PUB_URL, HUNT_URL
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode


class ChatService:
    CSRF_SOURCE_BY_MODE: dict[Mode, str] = {
        Mode.IDLE: PUB_URL,
        Mode.TRAINING: PUB_URL,
        Mode.SOLO_HUNT: HUNT_URL,
        Mode.PHANTOM_HALLS: HUNT_URL,
        Mode.DEEP_DRAGON: HUNT_URL,
    }

    def __init__(self, account: Account):
        self.account = account

    def post_message(self, message: str, channel: str = "global"):
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
                "origin": BASE_URL,
                "referer": referer_url,
                "x-csrf-token": csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
            timeout=10,
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

        response = self.account.session.get(source_url, timeout=10)
        response.raise_for_status()

        return self._get_csrf(response.text)

    def _get_csrf(self, html: str) -> str:
        match = re.search(r'globalCsrfToken\s*=\s*"([a-f0-9]+)"', html)
        if not match:
            raise RuntimeError("CSRF token not found in PUB")
        return match.group(1)
