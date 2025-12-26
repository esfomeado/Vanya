import logging
import re
import time
from typing import Optional

from bs4 import BeautifulSoup

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
        resp = self.account.session.get(ADVENTURE_URL, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        bosses: list[Boss] = []

        for card in soup.select("a.boss-card.unlocked"):
            if card.select_one("span:contains('DEAD')"):
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

            boosted = "boosted" in card.get("class", [])

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
            try:
                self.attack_boss_once(boss.boss_id)
            except Exception as e:
                logging.warning(
                    f"Boss hit failed | account={self.account.username} | boss={boss.name} | err={e}"
                )

    def kill_boss(self, boss_id: int):
        self.boss_id = boss_id

        self.account.mode = Mode.BOSSES

    def tick(self):
        data = self.attack_boss_once(self.boss_id)

        if data.get("new_stamina", 0) <= 5:
            self.pub_service.go_to_pub()
            time.sleep(60)

        if data.get("new_player_life", 0) <= 100:
            self.pub_service.go_to_pub()

    def attack_boss_once(self, boss_id: int) -> dict:
        csrf = self._fetch_csrf()

        resp = self.account.session.post(
            ADVENTURE_ATTACK_URL,
            json={
                "boss_id": boss_id,
                "recaptcha_token": "",
            },
            headers={
                "origin": "https://vanyaonline.com",
                "referer": f"{ADVENTURE_URL}?boss_id={boss_id}",
                "x-csrf-token": csrf,
                "content-type": "application/json",
            },
            timeout=10,
        )
        resp.raise_for_status()

        data = resp.json()
        if data.get("status") != "ok":
            raise RuntimeError(f"Boss attack failed: {data}")

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

    def _parse_title(self, text: str):
        m = re.match(r"Stage\s+(\d+):\s+(.+)", text)
        return int(m.group(1)), m.group(2)

    def _parse_life_xp(self, info):
        text = info.get_text(" ", strip=True)
        m = re.search(r"Life:\s*([\d,]+)\s*\|\s*XP:\s*([\d,]+)", text)
        return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))

    def _parse_required_level(self, info):
        m = re.search(r"Required Level:\s*(\d+)", info.get_text())
        return int(m.group(1))

    def _fetch_csrf(self) -> str:
        resp = self.account.session.get(ADVENTURE_URL, timeout=10)
        resp.raise_for_status()
        match = re.search(r'globalCsrfToken\s*=\s*"([a-f0-9]+)"', resp.text)
        if not match:
            raise RuntimeError("CSRF token not found on adventure page")
        return match.group(1)
