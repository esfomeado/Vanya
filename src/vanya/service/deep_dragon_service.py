import logging
import re
import subprocess
import time
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import DEEP_DRAGON_URL, DUNGEON_VIEW_URL, HUNT_URL
from src.vanya.core.errors import VanyaError
from src.vanya.model.account import Account
from src.vanya.model.hunt import Hunt
from src.vanya.model.mode import Mode
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry


class DeepDragonService:
    DEFAULT_DURATION = 1810

    def __init__(self, account: Account):
        self.account = account
        self.last_hunt_start_time = 0
        self.tracked_hunters = {}
        self.duration = self.DEFAULT_DURATION
        self.pub_service = service_registry.get(PubService, account)

    def hunt(self, duration: Optional[int] = DEFAULT_DURATION, train: bool = True) -> None:
        logging.info(f"Starting deep dragon hunt for {self.account.username}")

        self.duration = duration

        generate_response = self.account.session.post(
            DEEP_DRAGON_URL,
            data={
                "csrf_token": self.account.csrf,
                "action": "generate",
                "mode": "solo",
                "duration": f"{self.duration}"
            },
            headers={
                "referer": DEEP_DRAGON_URL,
            }
        )

        page_html = generate_response.text

        while self._parse_difficulty(page_html) not in {"Void", "Inferno"}:
            max_hit = self._parse_max_hit(page_html)

            logging.info(
                f"Difficulty not Void: {self._parse_difficulty(page_html)}. Max hit {max_hit}. Rerolling for {self.account.username}...")

            reroll_response = self.account.session.post(
                DEEP_DRAGON_URL,
                data={
                    "csrf_token": self.account.csrf,
                    "action": "reroll"
                },
                headers={
                    "referer": DEEP_DRAGON_URL,
                }
            )
            page_html = reroll_response.text
            time.sleep(5)

        max_hit = self._parse_max_hit(page_html)

        self.account.session.post(
            DEEP_DRAGON_URL,
            data={
                "csrf_token": self.account.csrf,
                "action": "start"
            },
            headers={
                "csrf_token": self.account.csrf,
                "action": "start"
            }
        )

        self.account.mode = Mode.DEEP_DRAGON
        self.account.hunt = Hunt(area_id="deep_dragon", name="Deep Dragon", max_hit=max_hit)
        self.last_hunt_start_time = time.time()

        if train:
            self.pub_service.stop_training()
            self._manage_training_service("start")

        logging.info(
            f"Deep Dragon started for {self.account.username}. Max hit {max_hit}. Timer set for {duration}s.")

    def _parse_difficulty(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        for div in soup.find_all("div", class_="mini"):
            if "Difficulty:" in div.get_text():
                match = re.search(r"Difficulty:\s*<b[^>]*>(.*?)</b>", str(div), re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return None

    def _parse_max_hit(self, html: str) -> int:
        soup = BeautifulSoup(html, "html.parser")
        reward_divs = soup.select(".reward .r")

        for div in reward_divs:
            small_tag = div.find("small")
            if small_tag and "Incoming DMG" in small_tag.get_text():
                span_tag = div.find("span")
                if span_tag:
                    text = span_tag.get_text(strip=True)
                    match = re.search(r'[\d,]+(?:\s*[\-\–\—]\s*)([\d,]+)', text)
                    if match:
                        return int(match.group(1).replace(",", ""))

        raise VanyaError("Failed to parse max hit from Deep Dragon page")

    def tick(self) -> None:
        if self.last_hunt_start_time > 0 and (time.time() - self.last_hunt_start_time >= self.duration):
            logging.info(f"Deep Dragon timer finished for {self.account.username}. Claiming and restarting.")
            self.claim_rewards()
            self._manage_training_service("stop")
            self.pub_service.regenerate(sleep=False)
            self.hunt()
            return

        response = self.account.session.get(DEEP_DRAGON_URL)

        current_health, max_health = self.parse_current_health(response.text)
        potion_count = self.parse_potion_count(response.text)

        if 10 > potion_count > -1:
            logging.info(f"Potion count low ({potion_count}) for {self.account.username}. Buying more.")
            self.buy_potions()

        if self.account.hunt.max_hit * 4 >= current_health > -1:
            logging.info(f"Low health ({current_health}) detected for {self.account.username}. Using potion.")
            self.use_potion()

    def claim_rewards(self) -> None:
        logging.info(f"Claiming Deep Dragon rewards for {self.account.username}")
        try:
            self.account.session.post(
                DEEP_DRAGON_URL,
                data={
                    "csrf_token": self.account.csrf,
                    "action": "claim"
                },
                headers={
                    "referer": DEEP_DRAGON_URL,
                }
            )

            logging.info(f"Successfully claimed rewards for {self.account.username}")
        except Exception as e:
            logging.error(f"Failed to claim rewards for {self.account.username}: {e}")

    def parse_current_health(self, html: str) -> tuple[int, int]:
        soup = BeautifulSoup(html, "html.parser")

        life_now_el = soup.find("b", id="lifeNow")
        life_max_el = soup.find("b", id="lifeMax")

        current_life = 0
        max_life = 0

        if life_now_el:
            current_life = int(life_now_el.get_text(strip=True).replace(",", ""))

        if life_max_el:
            max_life = int(life_max_el.get_text(strip=True).replace(",", ""))

        return current_life, max_life

    def parse_potion_count(self, html: str) -> int:
        soup = BeautifulSoup(html, "html.parser")
        button = soup.find("button", string=re.compile(r"USE LIFE POTION", re.IGNORECASE))
        if button:
            match = re.search(r"\((\d+)\)", button.get_text())
            if match:
                return int(match.group(1))
        return -1

    def buy_potions(self) -> None:
        try:
            self.account.session.post(
                DEEP_DRAGON_URL,
                data={
                    "csrf_token": self.account.csrf,
                    "action": "buy_potion",
                    "qty": "10"
                },
                headers={
                    "referer": DEEP_DRAGON_URL,
                }
            )

            logging.info(f"Successfully bought potions for {self.account.username}")
        except Exception as e:
            logging.error(f"Failed to buy potion for {self.account.username}: {e}")

    def use_potion(self) -> None:
        try:
            self.account.session.post(
                DEEP_DRAGON_URL,
                data={
                    "csrf_token": self.account.csrf,
                    "action": "use_potion"
                },
                headers={
                    "referer": DEEP_DRAGON_URL,
                }
            )

            logging.info(f"Potion used successfully for {self.account.username}")
        except Exception as e:
            logging.error(f"Failed to use potion for {self.account.username}: {e}")

    def stop_hunt(self) -> None:
        logging.info(f"Stopping Deep Dragon hunt for {self.account.username}")

        self.account.session.post(
            DEEP_DRAGON_URL,
            data={
                "csrf_token": self.account.csrf,
                "action": "escape"
            },
            headers={
                "referer": DEEP_DRAGON_URL,
            }
        )

        self.account.hunt = None
        self.account.mode = Mode.IDLE
        self._manage_training_service("stop")

        logging.info(f"Successfully escaped Deep Dragon for {self.account.username}")

    def _manage_training_service(self, action: str) -> None:
        try:
            subprocess.run(["sudo", "systemctl", action, "vanya-training.service"], check=True)
            time.sleep(10)
            logging.info(f"Successfully {action}ed vanya-training.service")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to {action} vanya-training.service: {e}")

    def check_tracked_hunters(self) -> None:
        response = self.account.session.get(DEEP_DRAGON_URL)
        page_html = response.text
        now = time.time()

        hunters = self._parse_active_hunters(page_html)
        target = "Whisper"

        if target in hunters and target not in self.tracked_hunters:
            logging.info(f"Whisper's hunt is starting for {self.account.username}")
            self.tracked_hunters[target] = now + (hunters[target] * 60)

        if target in self.tracked_hunters:
            time_left = self.tracked_hunters[target] - now
            if 0 < time_left <= 600:
                if self._is_user_hunting(target):
                    self._execute_tracked_action()
                    del self.tracked_hunters[target]

    def _parse_active_hunters(self, html: str) -> dict[str, int]:
        soup = BeautifulSoup(html, "html.parser")
        hunters = {}
        for item in soup.select(".list .item"):
            name_el = item.select_one(".name")
            meta_el = item.select_one(".meta")
            if name_el and meta_el:
                name = name_el.get_text(strip=True)
                match = re.search(r"(\d+)m", meta_el.get_text(strip=True))
                if match:
                    hunters[name] = int(match.group(1))
        return hunters

    def _execute_tracked_action(self) -> None:
        logging.info("Whisper's hunt is ending soon! Killing him...")

        self.account.session.post(
            DUNGEON_VIEW_URL,
            data={
                "ritual_dead": "1",
                "area_id": "dead_inside",
                "csrf_token": self.account.csrf,
                "target_user_id": "110",
                "pay_currency": "auto"
            },
            headers={
                "referer": DUNGEON_VIEW_URL
            }
        )

    def _is_user_hunting(self, target: str) -> bool:
        response = self.account.session.get(HUNT_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.find("img", alt=target) is not None
