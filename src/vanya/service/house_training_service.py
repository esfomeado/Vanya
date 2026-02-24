from src.vanya.core.constants import HOUSE_TRAIN_URL
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry


class HouseTrainingService:
    def __init__(self, account):
        self.account = account
        self.pub_service = service_registry.get(PubService, account)

    def train(self) -> None:
        self.pub_service.stop_training()

    def tick(self) -> None:
        self.account.session.post(
            HOUSE_TRAIN_URL,
            headers={
                "x-csrf-token": self.account.csrf,
            },
            data={
                "skill": "defense",
                "start": "0",
            },
        )
