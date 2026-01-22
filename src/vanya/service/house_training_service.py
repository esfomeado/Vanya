from src.vanya.core.constants import PUB_URL, PUB_OFFLINE_TRAIN_URL, HOUSE_TRAIN_URL, HOUSE_URL
from src.vanya.core.utils import get_global_csrf


class HouseTrainingService:
    def __init__(self, account):
        self.account = account

    def train(self):
        response = self.account.session.get(PUB_URL, timeout=10)
        csrf = get_global_csrf(response.text)

        self.account.session.post(
            PUB_OFFLINE_TRAIN_URL,
            data={
                "action": "stop"
            },
            headers={
                "origin": "https://vanyaonline.com",
                "referer": PUB_URL,
                "x-csrf-token": csrf,
                "content-type": "application/x-www-form-urlencoded",
            },
            timeout=10,
        ).raise_for_status()

    def tick(self):
        response = self.account.session.get(HOUSE_URL, timeout=10)
        csrf = get_global_csrf(response.text)

        self.account.session.post(
            HOUSE_TRAIN_URL,
            headers={
                "origin": "https://vanyaonline.com",
                "x-csrf-token": csrf,
            },
            data={
                "skill": "defense",
                "start": "0",
            },
        )
