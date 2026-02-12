import logging

from src.vanya.core.constants import BASE_URL
from src.vanya.core.utils import get_global_csrf
from src.vanya.model.account import Account


class LoungeService:
    def __init__(self, account: Account):
        self.account = account

    def like(self, topic_id: int, post_id: int) -> None:
        url = f"{BASE_URL}/view_topic?id={topic_id}"

        try:
            response = self.account.session.get(url)
            response.raise_for_status()
            csrf = get_global_csrf(response.text)

            self.account.session.post(
                url,
                json={
                    "action": "vote",
                    "post_id": post_id,
                    "vote": "hype",
                    "csrf_token": ""
                },
                headers={
                    "referer": url,
                    "origin": BASE_URL,
                    "content-type": "application/json",
                    "x-csrf-token": csrf,
                }
            ).raise_for_status()

            logging.info(f"Liked post {post_id} in topic {topic_id} for {self.account.username}")

        except Exception as e:
            logging.error(f"Failed to like post {post_id}: {e}")

    def dislike(self, topic_id: int, post_id: int) -> None:
        url = f"{BASE_URL}/view_topic?id={topic_id}"

        try:
            response = self.account.session.get(url)
            response.raise_for_status()
            csrf = get_global_csrf(response.text)

            self.account.session.post(
                url,
                json={
                    "action": "vote",
                    "post_id": post_id,
                    "vote": "dislike",
                    "csrf_token": ""
                },
                headers={
                    "referer": url,
                    "origin": BASE_URL,
                    "content-type": "application/json",
                    "x-csrf-token": csrf,
                }
            ).raise_for_status()

            logging.info(f"Disliked post {post_id} in topic {topic_id} for {self.account.username}")

        except Exception as e:
            logging.error(f"Failed to dislike post {post_id}: {e}")
