import logging
import re

from bs4 import BeautifulSoup, Tag

from src.vanya.core.constants import DASHBOARD_URL, EQUIP_URL
from src.vanya.model.account import Account


class AutoEquipService:
    _instances: dict[str, "AutoEquipService"] = {}

    def __new__(cls, account: Account):
        if account.username not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[account.username] = instance
            instance._initialized = False
        return cls._instances[account.username]

    def __init__(self, account: Account):
        if self._initialized:
            return

        self.account: Account = account
        self._initialized = True

    def equip(self):
        if not self.account.auto_equip:
            return

        response = self.account.session.get(DASHBOARD_URL, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        equipped = self._parse_equipped(soup)
        inventory = self._parse_inventory(soup)

        for slot, items in inventory.items():
            best = max(items, key=lambda x: x["defense"])
            current = equipped.get(slot)

            if not current or best["defense"] > current["defense"]:
                logging.info(f"Equipping {best['name']} (+{best['defense']} DEF) in {slot} on {self.account.username}")
                self._equip_item(best["name"], best["csrf"])

    def _parse_equipped(self, soup: BeautifulSoup) -> dict[str, dict]:
        equipped_stats = {}

        for d in soup.select(".equipped-item-detail"):
            name = d.select_one(".item-name-level").text.strip()
            defense = self._extract_defense_from_equipped(d)
            equipped_stats[name] = defense

        slots = {}
        for slot in soup.select(".equipment-slot.equipped"):
            cls = slot.get("class", [])
            slot_type = next(c.replace("slot-", "").upper() for c in cls if c.startswith("slot-"))
            item = slot.get("title")

            slots[slot_type] = {
                "name": item,
                "defense": equipped_stats.get(item, 0),
            }

        return slots

    def _extract_defense_from_equipped(self, detail_el: Tag):
        for bonus in detail_el.select(".item-bonus"):
            if "Defense" in bonus.text:
                m = re.search(r'\+(\d+)', bonus.text)
                if m:
                    return int(m.group(1))
        return 0

    def _parse_inventory(self, soup: BeautifulSoup) -> dict[str, list[dict]]:
        inventory = {}

        for item in soup.select(".inventory-item"):
            slot = item.get("data-slot")
            if not slot:
                continue

            title = item.get("title", "")
            defense = self._extract_defense_from_inventory(title)

            name_input = item.select_one("input[name=item_name]")
            csrf_input = item.select_one("input[name=csrf_token]")
            if not name_input or not csrf_input:
                continue

            inventory.setdefault(slot, []).append({
                "name": name_input.get("value"),
                "defense": defense,
                "csrf": csrf_input.get("value"),
            })

        return inventory

    def _extract_defense_from_inventory(self, text: str):
        if not text:
            return 0

        patterns = [
            r'Defense:\s*\+(\d+)',
            r'\+(\d+)\s*Defense',
        ]

        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return int(m.group(1))

        return 0

    def _equip_item(self, item_name: str, csrf: str):
        self.account.session.post(
            EQUIP_URL,
            data={
                "action": "equip",
                "item_name": item_name,
                "csrf_token": csrf,
            },
            headers={"referer": DASHBOARD_URL},
            timeout=10,
        ).raise_for_status()
