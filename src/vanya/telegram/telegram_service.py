import httpx

from src.vanya.core.config_loader import CONFIG


class TelegramService:
    def __init__(self):
        self._base_url = f"https://api.telegram.org/bot{CONFIG.telegram.token}"
        self._users = CONFIG.telegram.allowed_users
        self._client = httpx.Client(timeout=10)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def send(self, text: str):
        for user_id in self._users:
            self._client.post(
                f"{self._base_url}/sendMessage",
                json={"chat_id": user_id, "text": text, "disable_web_page_preview": True},
            ).raise_for_status()
