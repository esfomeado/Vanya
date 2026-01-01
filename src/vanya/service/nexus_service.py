import logging
import time

from src.vanya.core.constants import NEXUS_URL, ADVENTURE_ATTACK_URL, ADVENTURE_URL, DASHBOARD_URL
from src.vanya.core.utils import get_global_csrf
from src.vanya.model.boss import NexusBoss


class NexusService:
    _boss_min_level = {
        1: 10,
        2: 45,
        3: 100,
        4: 130,
        5: 180,
        6: 250,
    }

    _boss_attack_threshold = {
        1: 100,
        2: 90,
        3: 50,
        4: 30,
        5: 25,
        6: 20,
    }

    def __init__(self, account):
        self.account = account
        self.bosses: dict[int, NexusBoss] = {}
        self._hits: dict[int, float] = {}

    def refresh(self) -> None:
        url = f"{NEXUS_URL}?ajax_nexus_data=1&_={int(time.time() * 1000)}"
        response = self.account.session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        seen = set()
        for boss_id_str, info in data.get("bosses", {}).items():
            boss_id = int(boss_id_str)
            seen.add(boss_id)

            is_alive = info.get("is_alive", False)
            current_life = info.get("current_life", 0)
            max_life = info.get("max_life", 0)
            life_percent = (current_life / max_life * 100) if max_life else 0

            respawn_at = info.get("respawn_at", 0)

            if boss_id in self.bosses:
                boss = self.bosses[boss_id]
                boss.current_life = current_life
                boss.max_life = max_life
                boss.life_percent = life_percent
                boss.is_alive = is_alive
                boss.respawn_at = respawn_at
            else:
                self.bosses[boss_id] = NexusBoss(
                    boss_id=boss_id,
                    name=info.get("name", ""),
                    image=info.get("image", ""),
                    current_life=current_life,
                    max_life=max_life,
                    life_percent=life_percent,
                    is_alive=is_alive,
                    respawn_at=respawn_at,
                )

            if not is_alive:
                self._hits.pop(boss_id, None)

        self._cleanup_hits()

    def tick(self) -> None:
        for boss_id, boss in self.bosses.items():
            if not boss.is_alive:
                continue

            if self._should_attack(boss_id):
                try:
                    self._attack_boss_once(boss_id)
                    self._record_attack(boss_id)
                    logging.info(f"Attacked boss {boss.name}")
                except Exception as e:
                    logging.error(f"Failed to attack boss {boss.name}: {e}")

    def _attack_boss_once(self, boss_id: int) -> None:
        response = self.account.session.get(DASHBOARD_URL, timeout=10)
        response.raise_for_status()

        csrf = get_global_csrf(response.text)

        self.account.session.post(
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
        ).raise_for_status()

    def _should_attack(self, boss_id: int) -> bool:
        boss = self.bosses.get(boss_id)
        if not boss:
            return False

        if not boss.is_alive:
            return False

        if boss_id in self._hits:
            return False

        if self.account.stats.stamina <= 10:
            return False

        if self.account.stats.level < self._boss_min_level.get(boss_id, 99999):
            return False

        threshold = self._boss_attack_threshold.get(boss_id, 0)

        return boss.life_percent <= threshold

    def _record_attack(self, boss_id: int) -> None:
        self._hits[boss_id] = time.monotonic()

    def _cleanup_hits(self) -> None:
        now = time.monotonic()
        expired = [
            boss_id
            for boss_id, ts in self._hits.items()
            if now - ts >= 30 * 60
        ]
        for boss_id in expired:
            logging.info(f"Cleaned up hit for boss - expired {self.bosses[boss_id].name}")
            self._hits.pop(boss_id, None)
