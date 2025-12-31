import logging

from bs4 import BeautifulSoup

from src.vanya.core.constants import DASHBOARD_URL
from src.vanya.model.account import Account


class StatsService:
    def __init__(self, account: Account):
        self.account = account

    def refresh_account_stats(self) -> None:
        response = self.account.session.get(DASHBOARD_URL, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        self.account.guild = None

        pills = soup.select(".profile .stat-pill")
        for pill in pills:
            text = pill.get_text(strip=True)
            if "Level" in text:
                self.account.stats.level = int(text.split("Level")[-1].strip())
            elif (img := pill.find("img")) and "assets/img/items/gold.png" in img.get("src", ""):
                raw = pill.find("strong").text
                value = raw.replace(",", "").replace("\xa0", "").strip()
                self.account.stats.gold = int(value)

            strong = pill.find("strong")
            span = pill.find("span")

            if strong and span:
                tag = strong.get_text(strip=True)
                name = span.get_text(strip=True)
                if tag.startswith("[") and tag.endswith("]"):
                    self.account.guild = f"{tag} {name}"
                    continue

        life_panel = soup.select_one(".card h3:-soup-contains('Life')")
        if life_panel:
            muted = life_panel.find_next("div", class_="muted").text
            health, max_health = muted.split("/")
            self.account.stats.health = int(health.strip())
            self.account.stats.max_health = int(max_health.strip())

        skills = soup.select(".stat-line")
        for skill in skills:
            name = skill.find("span").text.strip().lower()
            raw = skill.find("strong").text.strip()
            base = int(raw.split("(")[0].strip())
            bonus = 0
            if "(" in raw:
                bonus = int(raw.split("+")[1].split(")")[0])
            total = base + bonus

            if name == "sword":
                self.account.stats.sword = total
            elif name == "bow":
                self.account.stats.bow = total
            elif name == "magic":
                self.account.stats.magic = total
            elif name == "defense":
                self.account.stats.defence = total
            elif name == "fishing":
                self.account.stats.fishing = total

        stamina_h3 = soup.select_one("h3:-soup-contains('Stamina')")
        if stamina_h3:
            panel_title = stamina_h3.parent
            value_container = panel_title.find_next_sibling("div")
            value_muted = value_container.select_one(".muted")

            if value_muted and "/" in value_muted.text:
                current, _ = value_muted.text.split("/", 1)
                self.account.stats.stamina = int(
                    current.replace(",", "").strip()
                )
