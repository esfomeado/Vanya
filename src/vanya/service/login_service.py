import logging
import os
import pickle

from src.vanya.core.constants import BASE_URL, LOGIN_URL, DASHBOARD_URL
from src.vanya.core.errors import VanyaError
from src.vanya.core.utils import get_global_csrf
from src.vanya.model.account import Account

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
COOKIES_DIR = os.path.join(PROJECT_ROOT, "cookies")
os.makedirs(COOKIES_DIR, exist_ok=True)


class LoginService:
    def __init__(self, account: Account):
        self.account = account
        self.session = account.session

    def load_cookies(self) -> bool:
        path = self._cookie_path()
        if os.path.exists(path):
            with open(path, "rb") as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    self.session.cookies.jar.set_cookie(cookie)
            return True
        return False

    def save_cookies(self) -> None:
        path = self._cookie_path()
        with open(path, "wb") as f:
            pickle.dump(list(self.session.cookies.jar), f)

    def clear_cookies(self) -> None:
        self.session.cookies.jar.clear()

    def _cookie_path(self) -> str:
        return os.path.join(COOKIES_DIR, f"{self.account.username}.pkl")

    def login(self) -> None:
        self.clear_cookies()

        self.session.headers.update({
            "content-type": "application/x-www-form-urlencoded",
            "origin": BASE_URL,
        })

        self.session.get(LOGIN_URL)

        response = self.session.post(
            LOGIN_URL,
            headers={
                "referer": f"{BASE_URL}/index",
            },
            data={
                "username": self.account.username,
                "password": self.account.password
            },
            allow_redirects=True,
        )

        current_url = response.url.lower()
        response_text = response.text.lower()

        if "/login" in current_url:
            if "banned" in response_text or "suspended" in response_text:
                raise VanyaError(f"Account {self.account.username} is banned")
            raise VanyaError(f"Login failed for {self.account.username}")

        self.save_cookies()
        self.load_cookies()
        self._get_csrf_token()

        logging.info(f"Login successful for {self.account.username}")

    def _get_csrf_token(self) -> None:
        response = self.session.get(
            DASHBOARD_URL,
        )

        self.account.csrf = get_global_csrf(response.text)
