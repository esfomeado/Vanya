import logging
import os
import pickle

from bs4 import BeautifulSoup

from src.vanya.core.constants import BASE_URL, LOGIN_URL, CHECK_HUNT_STATUS_URL, HUNT_URL, DASHBOARD_URL
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.phantom_halls_service import PhantomHallsService
from src.vanya.service.solo_hunt_service import SoloHuntService

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
COOKIES_DIR = os.path.join(PROJECT_ROOT, "cookies")
os.makedirs(COOKIES_DIR, exist_ok=True)


class LoginService:
    def __init__(self, account: Account):
        self.account = account
        self.session = account.session

        self.init_session()

    def cookie_path(self) -> str:
        return os.path.join(COOKIES_DIR, f"{self.account.username}.pkl")

    def load_cookies(self) -> bool:
        path = self.cookie_path()
        if os.path.exists(path):
            with open(path, "rb") as f:
                self.session.cookies.update(pickle.load(f))
            return True
        return False

    def save_cookies(self) -> None:
        path = self.cookie_path()
        with open(path, "wb") as f:
            pickle.dump(self.session.cookies, f)

    def init_session(self) -> None:
        self.session.headers.update({
            "accept": "text/html,application/xhtml+xml",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })

    def login(self) -> None:
        self.session.headers.update({
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "content-type": "application/x-www-form-urlencoded",
            "origin": BASE_URL,
            "referer": f"{BASE_URL}/index",
        })

        self.session.get(LOGIN_URL)

        response = self.session.post(
            LOGIN_URL,
            data={
                "username": self.account.username,
                "password": self.account.password
            },
            allow_redirects=True,
        )
        response.raise_for_status()

        if "/login" in response.url.lower():
            raise RuntimeError(f"Login failed for {self.account.username}")

        self.save_cookies()

        logging.info(f"Login successful for {self.account.username}")

    def ensure_logged_in(self) -> None:
        if self.load_cookies():
            try:
                response = self.session.get(
                    DASHBOARD_URL,
                    allow_redirects=False,
                )
                response.raise_for_status()

                if response.status_code == 200:
                    return
            except Exception as e:
                logging.info(f"Cookie validation failed for {self.account.username}: {e}")

        logging.info(f"Session expired for {self.account.username}")

        self.login()

    def reconcile_mode(self) -> None:
        try:
            response = self.account.session.get(CHECK_HUNT_STATUS_URL)
            response.raise_for_status()
            json_response = response.json()
            in_hunt = json_response.get("in_hunt", False)

            if self.account.mode in {Mode.IDLE, Mode.TRAINING} and in_hunt:
                self.account.mode = self._get_current_hunt_mode()
                if self.account.mode == Mode.SOLO_HUNT:
                    SoloHuntService(self.account).stop_hunt()
                    SoloHuntService(self.account).hunt()
                if self.account.mode == Mode.PHANTOM_HALLS:
                    PhantomHallsService(self.account).stop_hunt()
                    PhantomHallsService(self.account).hunt()
            elif self.account.mode in {Mode.SOLO_HUNT, Mode.PHANTOM_HALLS, Mode.DEEP_DRAGON} and not in_hunt:
                self.account.mode = Mode.IDLE
                self.account.hunt = None

        except Exception as e:
            logging.warning(f"Failed to reconcile mode for {self.account.username}: {e}")

    def _get_current_hunt_mode(self) -> Mode:
        hunt_name_to_mode = {
            "Dark Forest": Mode.SOLO_HUNT,
            "Dead River": Mode.SOLO_HUNT,
            "Forgotten Caverns": Mode.SOLO_HUNT,
            "Dragon Peaks": Mode.SOLO_HUNT,
            "Ashen Wastelands": Mode.SOLO_HUNT,
            "Crimson Depths": Mode.SOLO_HUNT,
            "Celestial Ruins": Mode.SOLO_HUNT,
            "Eternal Void": Mode.SOLO_HUNT,
            "Abyssal Gate": Mode.SOLO_HUNT,
            "Demon Fortress": Mode.SOLO_HUNT,
            "Abyss of Vanya": Mode.SOLO_HUNT,
            "Shadow Throne": Mode.PHANTOM_HALLS,
            "Astral Nexus": Mode.PHANTOM_HALLS,
            "Demona Edge": Mode.PHANTOM_HALLS,
            "The Penumbula": Mode.PHANTOM_HALLS,
            "The Ossuary Lord": Mode.PHANTOM_HALLS,
        }

        try:
            response = self.account.session.get(HUNT_URL)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            h1 = soup.select_one(".hunt-container h1")
            if not h1:
                logging.warning(f"Failed to get hunt name for {self.account.username}")
                return Mode.SOLO_HUNT

            hunt_text = h1.get_text(strip=True)
            if "Hunting in " in hunt_text:
                name = hunt_text.split("Hunting in ")[1].split("(")[0].strip()
            else:
                name = hunt_text

            return hunt_name_to_mode.get(name, Mode.SOLO_HUNT)

        except Exception as e:
            logging.warning(f"Failed to get current hunt mode for {self.account.username}: {e}")
            return Mode.SOLO_HUNT
