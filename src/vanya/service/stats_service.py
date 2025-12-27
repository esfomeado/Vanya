import logging

from bs4 import BeautifulSoup

from src.vanya.core.constants import DASHBOARD_URL
from src.vanya.model.account import Account


class StatsService:
    def __init__(self, account: Account):
        self.account = account

    def refresh_account_stats(self) -> None:
        logging.info(f"Refreshing stats for account {self.account.username}")

        response = self.account.session.get(DASHBOARD_URL, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        pills = soup.select(".profile .stat-pill")
        for pill in pills:
            text = pill.get_text(strip=True)
            if "Level" in text:
                self.account.stats.level = int(text.split("Level")[-1].strip())
            elif (img := pill.find("img")) and "assets/img/items/gold.png" in img.get("src", ""):
                raw = pill.find("strong").text
                value = raw.replace(",", "").replace("\xa0", "").strip()
                self.account.stats.gold = int(value)

        life_panel = soup.select_one(".card h3:contains('Life')")
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
