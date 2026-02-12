import logging
from typing import Optional

from src.vanya.core.constants import PUB_URL, PUB_TRAIN_CLICK_URL
from src.vanya.core.utils import get_global_csrf
from src.vanya.model.account import Account
from src.vanya.model.mode import Mode


class TrainingService:
    SKILL_TO_DUMMY_ID = {
        "defense": 5,
        "fishing": 4,
        "magic": 7,
        "sword": 2,
    }

    def __init__(self, account: Account):
        self.account = account
        self.skill: Optional[str] = None
        self.csrf: Optional[str] = None

    def tick(self) -> None:
        dummy_id = self.SKILL_TO_DUMMY_ID.get(self.skill)
        if dummy_id is None:
            logging.error(f"Unknown skill '{self.skill}' for account {self.account.username}")
            return

        try:
            self.csrf = self._fetch_csrf()
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
                    "referer": PUB_URL,
                    "x-csrf-token": self.csrf,
                    "content-type": "application/x-www-form-urlencoded",
                },
            )

            logging.info(f"Training tick | account={self.account.username} | skill={self.skill}")

        except Exception as e:
            logging.error(f"Failed training tick for {self.account.username}: {e}")

    def train(self, skill: str) -> None:
        self.skill = skill
        dummy_id = self.SKILL_TO_DUMMY_ID.get(skill.lower())

        if dummy_id is None:
            logging.error(f"Unknown skill '{self.skill}' for account {self.account.username}")
            return

        payload = {
            "dummy_id": str(dummy_id),
            "skill": skill,
            "start": str(0),
            "is_lite": str(0),
        }

        self.csrf = self._fetch_csrf()

        self.account.session.post(
            PUB_TRAIN_CLICK_URL,
            data=payload,
            headers={
                "referer": PUB_URL,
                "x-csrf-token": self.csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
        )

        self.account.mode = Mode.TRAINING

        logging.info(
            f"Training started | account={self.account.username} | skill={skill}"
        )

    def _fetch_csrf(self) -> str:
        response = self.account.session.get(PUB_URL)

        return get_global_csrf(response.text)
