import logging
import re

from bs4 import BeautifulSoup

from src.vanya.core.constants import MARKET_URL
from src.vanya.model.account import Account
from src.vanya.model.market import MarketListing


class DarkMarketService:
    def __init__(self, account: Account):
        self.account = account

    def list(self) -> list[MarketListing]:
        logging.info(f"Listing items for account {self.account.username}")

        response = self.account.session.get(
            MARKET_URL,
            headers={
                "accept": "text/html",
                "referer": MARKET_URL,
            },
        )

        soup = BeautifulSoup(response.text, "html.parser")
        listings: list[MarketListing] = []

        for box in soup.select(".listing-box"):
            strong_text = box.select_one("strong").text.strip()

            quantity = 1
            name = strong_text

            match = re.match(r'^(\d+)x\s+(.*)', strong_text)
            if match:
                quantity = int(match.group(1))
                name = match.group(2)

            meta_span = box.select_one(".item-details span")
            meta = meta_span.get_text(strip=True) if meta_span else ""

            stats_el = box.select_one(".item-stats")
            stats = stats_el.text.strip() if stats_el else ""

            price_text = box.select_one(".price-tag").text
            price = int(price_text.split()[0].replace(",", ""))

            form = box.select_one("form")
            listing_id = form.select_one("input[name=listing_id]")["value"]

            listings.append(
                MarketListing(
                    listing_id=int(listing_id),
                    name=name,
                    quantity=quantity,
                    price=price,
                    meta=meta,
                    stats=stats,
                )
            )

        return listings

    def buy_item(self, item_id: int) -> None:
        logging.info(f"Buying item {item_id}, for account {self.account.username}")

        self.account.session.post(
            MARKET_URL,
            headers={
                "referer": MARKET_URL,
            },
            data={
                "action": "buy_item",
                "listing_id": item_id,
                "csrf_token": self.account.csrf,
            },
        )

    def sell_item(self, item_name: str, amount: int, price: int) -> None:
        logging.info(f"Selling {amount}x {item_name} for {price} gold, for account {self.account.username}")

        if item_name == "Drako":
            self.sell_drako(amount, price)
            return

        self.account.session.post(
            MARKET_URL,
            headers={
                "referer": MARKET_URL,
            },
            data={
                "action": "list_item",
                "csrf_token": self.account.csrf,
                "item_name": item_name,
                "amount": amount,
                "price": price,
                "unbind_currency": "gold",
            },
        )

    def sell_drako(self, amount: int, price: int) -> None:
        logging.info(f"Selling {amount}x Drako for {price} gold, for account {self.account.username}")

        self.account.session.post(
            MARKET_URL,
            headers={
                "referer": MARKET_URL,
            },
            data={
                "action": "list_drako",
                "csrf_token": self.account.csrf,
                "drako_amount": amount,
                "price": price,
            },
        )
