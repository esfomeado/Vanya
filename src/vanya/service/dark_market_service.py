import logging
from src.vanya.core.constants import MARKET_URL, MARKET_ORDER_ACTION_URL
from src.vanya.model.account import Account
from src.vanya.model.market import MarketListing


class DarkMarketService:
    def __init__(self, account: Account):
        self.account = account

    def list(self) -> list[MarketListing]:
        logging.info(f"Listing items for account {self.account.username}")
        # The market now uses an order book model via JS and AJAX.
        # Direct parsing of listing boxes is no longer supported here.
        return []

    def buy_item(self, item_id: int) -> None:
        logging.info(f"Buying item {item_id}, for account {self.account.username}")

        self.account.session.post(
            MARKET_ORDER_ACTION_URL,
            headers={
                "referer": MARKET_URL,
            },
            data={
                "market_action": "fill_order",
                "order_id": item_id,
                "amount": 1,
                "csrf_token": self.account.csrf,
            },
        )

    def sell_item(self, item_name: str, amount: int, price: int) -> None:
        logging.info(f"Selling {amount}x {item_name} for {price} gold, for account {self.account.username}")

        if item_name == "Drako":
            self.sell_drako(amount, price)
            return

        unit_price = max(1, price // amount) if amount > 0 else price

        self.account.session.post(
            MARKET_ORDER_ACTION_URL,
            headers={
                "referer": MARKET_URL,
            },
            data={
                "market_action": "create_order",
                "side": "sell",
                "item_name": item_name,
                "currency": "gold",
                "amount": amount,
                "unit_price": unit_price,
                "csrf_token": self.account.csrf,
            },
        )

    def sell_drako(self, amount: int, price: int) -> None:
        logging.info(f"Selling {amount}x Drako for {price} gold, for account {self.account.username}")

        unit_price = max(1, price // amount) if amount > 0 else price

        self.account.session.post(
            MARKET_ORDER_ACTION_URL,
            headers={
                "referer": MARKET_URL,
            },
            data={
                "market_action": "create_order",
                "side": "sell",
                "item_name": "Drako",
                "currency": "gold",
                "amount": amount,
                "unit_price": unit_price,
                "csrf_token": self.account.csrf,
            },
        )
