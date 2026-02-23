import logging
import re
from typing import Optional

from bs4 import BeautifulSoup
from bs4.element import AttributeValueList

from src.vanya.core.constants import ADVENTURE_ATTACK_URL, ADVENTURE_URL
from src.vanya.model.account import Account
from src.vanya.model.boss import Boss
from src.vanya.model.mode import Mode
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry


class BossService:
    def __init__(self, account: Account):
        self.account = account
        self.pub_service = service_registry.get(PubService, account)
        self.boss_id: Optional[int] = None

    def list_available_bosses(self) -> list[Boss]:
        logging.info(f"Listing available bosses for account {self.account.username}")

        response = self.account.session.get(ADVENTURE_URL)

        soup = BeautifulSoup(response.text, "html.parser")
        bosses: list[Boss] = []

        for card in soup.select("a.boss-card.unlocked"):
            if card.select_one("span:-soup-contains('DEAD')"):
                continue

            status = card.get_text(strip=True)
            if "ALIVE" not in status:
                continue

            href = card.get("href", "")
            m = re.search(r"boss_id=(\d+)", href)
            if not m:
                continue
            boss_id = int(m.group(1))

            title = card.find("h3").text.strip()
            stage, name = self._parse_title(title)

            info = card.select_one(".boss-info")
            life, xp = self._parse_life_xp(info)
            required_level = self._parse_required_level(info)

            boosted = "boosted" in card.get("class", AttributeValueList())

            bosses.append(
                Boss(
                    boss_id=boss_id,
                    stage=stage,
                    name=name,
                    life=life,
                    xp=xp,
                    required_level=required_level,
                    boosted=boosted,
                )
            )

        return bosses

    def hit_each_available_boss_once(self) -> None:
        bosses = self.list_available_bosses()
        if not bosses:
            return

        for boss in bosses:
            current_life = self._get_boss_current_life(boss.boss_id)

            if current_life / boss.life > 0.5:
                continue

            try:
                self.attack_boss_once(boss.boss_id)
            except Exception as e:
                logging.warning(
                    f"Boss hit failed | account={self.account.username} | boss={boss.name} | err={e}"
                )

    def kill_boss(self, boss_id: int) -> None:
        self.boss_id = boss_id

        self.account.mode = Mode.BOSSES

    def tick(self) -> None:
        data = self.attack_boss_once(self.boss_id)

        if not data:
            self.account.mode = Mode.IDLE
            return

        if data.get("new_stamina", 0) <= 10:
            for _ in range(1):
                self.pub_service.regenerate()

        if data.get("new_player_life", 0) <= 250:
            self.pub_service.go_to_pub_and_heal()

    def attack_boss_once(self, boss_id: int) -> Optional[dict]:
        current_life = self._get_boss_current_life(boss_id)
        if current_life == 0:
            return None

        response = self.account.session.post(
            ADVENTURE_ATTACK_URL,
            json={
                "boss_id": boss_id,
                "recaptcha_token": "",
            },
            headers={
                "referer": f"{ADVENTURE_URL}?boss_id={boss_id}",
                "x-csrf-token": self.account.csrf,
            },
        )

        data = response.json()
        if data.get("status") != "ok":
            return None

        logging.info(
            "Boss hit | account=%s | boss=%s | dmg=%.1f | boss_hp=%.1f/%.1f | player_hp=%d/%d | stamina=%d",
            self.account.username,
            data.get("boss_name"),
            data.get("player_damage", 0),
            data.get("new_boss_life", 0),
            data.get("boss_max_life", 0),
            data.get("new_player_life", 0),
            data.get("player_max_life", 0),
            data.get("new_stamina", 0),
        )

        return data

    def farm(self) -> None:
        boss_id = 2

        boss_life = self._get_boss_current_life(boss_id)
        logging.info(f"{self.account.username}: Boss {boss_id} life: {boss_life}")

        if self.account.username == "Skyrus":
            if 0 < boss_life <= 450 and self.account.stats.stamina > 20:
                self.attack_boss_once(boss_id)
        else:
            if boss_life > 450 and self.account.stats.stamina > 20:
                self.attack_boss_once(boss_id)

    def _parse_title(self, text: str) -> tuple[int, str]:
        m = re.match(r"Stage\s+(\d+):\s+(.+)", text)
        return int(m.group(1)), m.group(2)

    def _parse_life_xp(self, info) -> tuple[int, int]:
        text = info.get_text(" ", strip=True)
        m = re.search(r"Life:\s*([\d,]+)\s*\|\s*XP:\s*([\d,]+)", text)
        return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))

    def _parse_required_level(self, info) -> int:
        m = re.search(r"Required Level:\s*(\d+)", info.get_text())
        return int(m.group(1))

    def _get_boss_current_life(self, boss_id: int) -> int:
        resp = self.account.session.get(
            f"{ADVENTURE_URL}?boss_id={boss_id}",
        )

        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.select_one("#boss-life-text").text
        cur, _ = text.split("/")
        return int(cur.replace(",", "").strip())
