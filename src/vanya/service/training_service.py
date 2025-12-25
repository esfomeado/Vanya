import logging
import re
from typing import Optional

from src.vanya.core.constants import PUB_URL, PUB_TRAIN_CLICK_URL
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode


class TrainingService:
    _instances: dict[str, "TrainingService"] = {}

    SKILL_TO_DUMMY_ID = {
        "defense": 5,
        "fishing": 4,
        "magic": 7,
        "sword": 2,
    }

    def __new__(cls, account: Account):
        if account.username not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[account.username] = instance
            instance._initialized = False
        return cls._instances[account.username]

    def __init__(self, account: Account):
        if self._initialized:
            return

        self.account = account
        self.skill: Optional[str] = None
        self._initialized = True

    def tick(self):
        dummy_id = self.SKILL_TO_DUMMY_ID.get(self.skill)
        if dummy_id is None:
            logging.warning(f"Unknown skill '{self.skill}' for account {self.account.username}")
            return

        try:
            csrf = self._fetch_csrf()
            payload = {
                "dummy_id": str(dummy_id),
                "skill": self.skill,
                "start": str(0),
                "is_lite": str(0),
            }

            self.account.session.post(
                PUB_TRAIN_CLICK_URL,
                data=payload,
                headers={
                    "origin": "https://vanyaonline.com",
                    "referer": PUB_URL,
                    "x-csrf-token": csrf,
                    "content-type": "application/x-www-form-urlencoded",
                },
                timeout=10,
            ).raise_for_status()

            logging.info(f"Training tick | account={self.account.username} | skill={self.skill}")

        except Exception as e:
            logging.warning(f"Failed training tick for {self.account.username}: {e}")

    def train(self, skill: str):
        self.skill = skill
        dummy_id = self.SKILL_TO_DUMMY_ID.get(skill.lower())

        if dummy_id is None:
            logging.warning(f"Unknown skill '{self.skill}' for account {self.account.username}")
            return

        csrf = self._fetch_csrf()

        payload = {
            "dummy_id": str(dummy_id),
            "skill": skill,
            "start": str(1),
            "is_lite": str(0),
        }

        self.account.session.post(
            PUB_TRAIN_CLICK_URL,
            data=payload,
            headers={
                "origin": "https://vanyaonline.com",
                "referer": PUB_URL,
                "x-csrf-token": csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        ).raise_for_status()

        self.account.mode = Mode.TRAINING

        logging.info(
            f"Training started | account={self.account.username} | skill={skill}"
        )

    def _fetch_csrf(self) -> str:
        response = self.account.session.get(PUB_URL, timeout=10)
        response.raise_for_status()
        return self._get_csrf(response.text)

    def _get_csrf(self, html: str) -> str:
        match = re.search(r'globalCsrfToken\s*=\s*"([a-f0-9]+)"', html)
        if not match:
            raise RuntimeError("CSRF token not found in PUB")
        return match.group(1)
