import logging

from src.vanya.core.constants import REDEEM_COUPON_URL
from src.vanya.core.constants import SETTINGS_URL
from src.vanya.model.account import Account


class CouponService:
    def __init__(self, account: Account):
        self.account = account

    def redeem(self, coupon_code: str) -> None:
        logging.info(f"Redeeming coupon {coupon_code} for account {self.account.username}")

        self.account.session.post(
            REDEEM_COUPON_URL,
            data={
                "code": coupon_code,
                "csrf_token": self.account.csrf
            },
            headers={
                "referer": SETTINGS_URL,
                "x-csrf-token": self.account.csrf,
            },
        )
