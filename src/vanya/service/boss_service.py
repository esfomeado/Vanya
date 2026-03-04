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
        self._next_farm_time: float = 0

    def list_available_bosses(self) -> list[Boss]:
        logging.info(f"Listing available bosses for account {self.account.username}")

        response = self.account.session.get(ADVENTURE_URL)

        soup = BeautifulSoup(response.text, "html.parser")
        bosses: list[Boss] = []

        for card in soup.select("a.boss-card.unlocked"):
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

            bosses.append(
                Boss(
                    boss_id=boss_id,
                    stage=stage,
                    name=name,
                    life=life,
                    xp=xp,
                    required_level=required_level,
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
                "mode": "global",
            },
            headers={
                "referer": f"{ADVENTURE_URL}?boss_id={boss_id}",
                "x-csrf-token": self.account.csrf,
            },
        )

        data = response.json()
        if data.get("status") == "human_check_required":
            logging.info(f"Human check required for {self.account.username}. Solving...")

            human_check = data.get("human_check", {})
            token = human_check.get("token")
            question = human_check.get("question")

            try:
                answer = self._solve_math_challenge(question)
                logging.info(f"Math Question: '{question}' -> Answer: '{answer}'")

                payload = {
                    "boss_id": boss_id,
                    "mode": "global",
                    "human_token": token,
                    "human_answer": answer,
                }

                response = self.account.session.post(
                    ADVENTURE_ATTACK_URL,
                    json=payload,
                    headers={
                        "referer": f"{ADVENTURE_URL}?boss_id={boss_id}",
                        "x-csrf-token": self.account.csrf,
                    },
                )
                data = response.json()

            except Exception as e:
                logging.exception(f"Failed to solve human check for {self.account.username}: {e}")
                return None

        if data.get("status") != "ok":
            logging.error(f"Failed to hit boss {data.get("message")}")
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
        if time.time() < self._next_farm_time:
            return

        boss_id = 2

        boss_life = self._get_boss_current_life(boss_id)
        if boss_life == 0:
            logging.info(f"{self.account.username}: Boss {boss_id} is dead. Waiting 10m.")
            self._next_farm_time = time.time() + 600
            return

        logging.info(f"{self.account.username}: Boss {boss_id} life: {boss_life}")

        if self.account.username == "Skyrus":
            if 0 < boss_life <= 550 and self.account.stats.stamina > 20:
                self.attack_boss_once(boss_id)
        else:
            if boss_life > 550 and self.account.stats.stamina > 20:
                self.attack_boss_once(boss_id)

    def _parse_title(self, text: str) -> tuple[int, str]:
        m = re.match(r"Stage\s+(\d+):\s+(.+)", text)
        return int(m.group(1)), m.group(2)

    def _parse_life_xp(self, info) -> tuple[int, int]:
        text = info.get_text(" ", strip=True)
        m = re.search(r"Life:\s*([\d,]+)\s*\|\s*XP:\s*([\d,]+)", text)
        return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))

    def _parse_required_level(self, info) -> int:
        text = info.get_text()
        m = re.search(r"(?:Required\s+)?Level:\s*(\d+)", text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        return 0

    def _get_boss_current_life(self, boss_id: int) -> int:
        resp = self.account.session.get(
            f"{ADVENTURE_URL}?boss_id={boss_id}",
        )

        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.select_one("#boss-life-text").text
        cur, _ = text.split("/")
        return int(cur.replace(",", "").strip())

    def _solve_math_challenge(self, question: str) -> str:
        match = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', question)
        if not match:
            raise ValueError(f"Could not parse math question: {question}")

        a = int(match.group(1))
        op = match.group(2)
        b = int(match.group(3))

        result = 0
        if op == '+':
            result = a + b
        elif op == '-':
            result = a - b
        elif op == '*':
            result = a * b
        elif op == '/':
            if b == 0:
                result = 0
            else:
                result = a // b

        return str(result)
