import logging

from bs4 import BeautifulSoup

from src.vanya.core.constants import MARKET_URL
from src.vanya.model.market import MarketListing


class DarkMarketService:
    def __init__(self, account):
        self.account = account

    def list(self) -> list[MarketListing]:
        response = self.account.session.get(
            MARKET_URL,
            headers={
                "accept": "text/html",
                "referer": MARKET_URL,
            },
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        listings: list[MarketListing] = []

        for box in soup.select(".listing-box"):
            name = box.select_one("strong").text.strip()

            meta = box.select_one(".item-details span").get_text(strip=True)

            stats_el = box.select_one(".item-stats")
            stats = stats_el.text.strip() if stats_el else ""

            price_text = box.select_one(".price-tag").text
            price = int(price_text.split()[0].replace(",", ""))

            form = box.select_one("form")
            listing_id = form.select_one("input[name=listing_id]")["value"]
            csrf = form.select_one("input[name=csrf_token]")["value"]

            listings.append(
                MarketListing(
                    listing_id=int(listing_id),
                    name=name,
                    price=price,
                    meta=meta,
                    stats=stats,
                    csrf_token=csrf,
                )
            )

        return listings

    def buy_item(self, item_id: int) -> None:
        response = self.account.session.get(
            MARKET_URL,
            headers={
                "accept": "text/html",
                "referer": MARKET_URL,
            },
        )
        response.raise_for_status()

        csrf = self._extract_list_csrf(response.text)

        self.account.session.post(
            MARKET_URL,
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "referer": MARKET_URL,
            },
            data={
                "action": "buy_item",
                "listing_id": item_id,
                "csrf_token": csrf,
            },
            follow_redirects=True,
        ).raise_for_status()

    def sell_item(self, item_name: str, amount: int, price: int) -> None:
        logging.info(f"Selling {amount}x {item_name} for {price} gold")
        response = self.account.session.get(
            MARKET_URL,
            headers={
                "accept": "text/html",
                "referer": MARKET_URL,
            },
        )
        response.raise_for_status()

        csrf = self._extract_list_csrf(response.text)

        self.account.session.post(
            MARKET_URL,
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "referer": MARKET_URL,
            },
            data={
                "action": "list_item",
                "csrf_token": csrf,
                "item_name": item_name,
                "amount": amount,
                "price": price,
                "unbind_currency": "gold",
            },
            follow_redirects=True,
        ).raise_for_status()

    def _extract_list_csrf(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        form = soup.select_one(".list-form form")
        if not form:
            raise RuntimeError("List form not found")

        token = form.select_one("input[name=csrf_token]")
        if not token:
            raise RuntimeError("CSRF token not found in list form")

        return token["value"]
