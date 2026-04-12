import re

from bs4 import BeautifulSoup

from src.vanya.core.constants import DASHBOARD_URL
from src.vanya.model.account import Account


class StatsService:
    def __init__(self, account: Account):
        self.account = account

    def refresh_account_stats(self) -> None:
        response = self.account.session.get(DASHBOARD_URL)
        soup = BeautifulSoup(response.text, "html.parser")

        self.account.guild = None

        pills = soup.select(".stat-pill")
        for pill in pills:
            text = pill.get_text(" ", strip=True)

            if "Level" in text:
                match = re.search(r"Level\s+(\d+)", text)
                if match:
                    self.account.stats.level = int(match.group(1))

            img_gold = pill.find("img", src=re.compile("gold.png"))
            if img_gold:
                val = pill.find("span", class_="val")
                if val:
                    self.account.stats.gold = int(val.text.replace(",", "").strip())

            img_drako = pill.find("img", src=re.compile("drako.png"))
            if img_drako:
                val = img_drako.find_next("span", class_="val")
                if val:
                    self.account.stats.drako = int(val.text.replace(",", "").strip())

            strong = pill.find("strong")
            if strong:
                tag = strong.get_text(strip=True)
                if tag.startswith("[") and tag.endswith("]"):
                    span = strong.find_next_sibling("span")
                    if span:
                        name = span.get_text(strip=True)
                        self.account.guild = f"{tag} {name}"

        hash_guard_text = soup.find(string=re.compile(r"Hash Guard", re.IGNORECASE))
        if hash_guard_text and hash_guard_text.parent:
            match = re.search(r"(\d+)/\d+", hash_guard_text.parent.text)
            if match:
                self.account.stats.hashed_accounts = int(match.group(1))

        life_h3 = None
        for h3 in soup.find_all("h3"):
            if "Life" in h3.get_text(strip=True):
                life_h3 = h3
                break

        if life_h3:
            muted = life_h3.find_next_sibling("div", class_="muted")
            if muted and "/" in muted.text:
                health, max_health = muted.text.split("/")
                self.account.stats.health = int(health.replace(",", "").strip())
                self.account.stats.max_health = int(max_health.replace(",", "").strip())

        skills = soup.select(".stat-line")
        for skill in skills:
            name_el = skill.find("span")
            strong_el = skill.find("strong")
            if not name_el or not strong_el:
                continue

            name = name_el.text.strip().lower()
            raw = strong_el.text.strip()

            try:
                base = int(raw.split("(")[0].replace(",", "").strip())
                bonus = 0
                if "(" in raw:
                    bonus_str = raw.split("+")[1].split(")")[0].replace(",", "").strip()
                    bonus = int(bonus_str)
                total = base + bonus
            except ValueError:
                continue

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

        stamina_h3 = None
        for h3 in soup.find_all("h3"):
            if "Stamina" in h3.get_text(strip=True):
                stamina_h3 = h3
                break

        if stamina_h3:
            panel_title = stamina_h3.find_parent("div", class_="panel-title")
            if panel_title:
                value_container = panel_title.find_next_sibling("div")
                if value_container:
                    value_muted = value_container.find("div", class_="muted")
                    if value_muted and "/" in value_muted.text:
                        current, _ = value_muted.text.split("/", 1)
                        self.account.stats.stamina = int(current.replace(",", "").strip())
