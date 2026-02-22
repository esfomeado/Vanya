import logging

from src.vanya.core.constants import BASE_URL
from src.vanya.core.constants import PUB_MURAL_POST_URL
from src.vanya.model.account import Account


class ChatService:
    def __init__(self, account: Account):
        self.account = account

    def post_message(self, message: str, channel: str = "global") -> None:
        self.account.session.post(
            PUB_MURAL_POST_URL,
            data={
                "message": message,
                "channel": channel,
            },
            headers={
                "referer": f"{BASE_URL}/pub_chat_only",
                "x-csrf-token": self.account.csrf,
            },
        )

        logging.info(
            "Chat message sent | account=%s | channel=%s",
            self.account.username,
            channel,
        )
