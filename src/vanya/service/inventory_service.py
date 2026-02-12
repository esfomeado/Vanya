import re

from bs4 import BeautifulSoup

from src.vanya.core.constants import DASHBOARD_URL
from src.vanya.model.account import Account
from src.vanya.model.item import InventoryItem


class InventoryService:
    def __init__(self, account: Account):
        self.account = account

    def list_items(self) -> list[InventoryItem]:
        response = self.account.session.get(DASHBOARD_URL)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        inventory = soup.select_one(".inventory.inventory-grid")
        if not inventory:
            return []

        items: list[InventoryItem] = []

        for el in inventory.select(".inventory-item"):
            slot = el.get("data-slot")

            name_el = el.select_one("div[style*='font-weight:700']")
            if not name_el:
                continue

            name = name_el.get_text(strip=True)
            equipped = "[E]" in name
            name = name.replace("[E]", "").strip()

            qty_el = el.select_one(".muted")
            quantity = 1
            equippable = False
            if qty_el:
                m = re.search(r"x(\d+)", qty_el.get_text())
                if m:
                    quantity = int(m.group(1))
                equippable = "Equippable" in qty_el.get_text()

            stats_el = el.select_one(".item-stats")
            stats = stats_el.get_text(strip=True) if stats_el else None

            img = el.select_one("img")
            image = img.get("src") if img else ""

            items.append(
                InventoryItem(
                    name=name,
                    slot=slot,
                    quantity=quantity,
                    equippable=equippable,
                    equipped=equipped,
                    stats=stats,
                    image=image,
                )
            )

        return items
