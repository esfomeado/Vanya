import logging
import re
import time
from typing import Optional

from bs4 import BeautifulSoup

from src.vanya.core.constants import BASE_URL
from src.vanya.core.constants import DEEP_DRAGON_URL
from src.vanya.core.errors import VanyaError
from src.vanya.model.hunt import Hunt
from src.vanya.model.mode import Mode
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry


class DeepDragonService:
    DURATION = 1800

    def __init__(self, account):
        self.account = account
        self.last_hunt_start_time = 0
        self.pub_service = service_registry.get(PubService, account)

    def hunt(self) -> None:
        logging.info(f"Starting deep dragon hunt for {self.account.username}")

        response = self.account.session.get(DEEP_DRAGON_URL)
        response.raise_for_status()
        csrf = self._get_csrf(response.text)

        generate_response = self.account.session.post(
            DEEP_DRAGON_URL,
            data={
                "csrf_token": csrf,
                "action": "generate",
                "mode": "solo",
                "duration": f"{self.DURATION}"
            },
            headers={
                "referer": DEEP_DRAGON_URL,
                "origin": BASE_URL,
                "content-type": "application/x-www-form-urlencoded"
            }
        )
        generate_response.raise_for_status()

        page_html = generate_response.text

        while self._parse_difficulty(page_html) != "Void":
            logging.info(f"Difficulty not Void. Rerolling for {self.account.username}...")

            reroll_response = self.account.session.post(
                DEEP_DRAGON_URL,
                data={
                    "csrf_token": csrf,
                    "action": "reroll"
                },
                headers={
                    "referer": DEEP_DRAGON_URL,
                    "origin": BASE_URL,
                    "content-type": "application/x-www-form-urlencoded"
                }
            )
            reroll_response.raise_for_status()
            page_html = reroll_response.text
            time.sleep(5)

        max_hit = self._parse_max_hit(page_html)

        self.account.session.post(
            DEEP_DRAGON_URL,
            data={
                "csrf_token": csrf,
                "action": "start"
            },
            headers={
                "csrf_token": csrf,
                "action": "start"
            }
        ).raise_for_status()

        self.account.mode = Mode.DEEP_DRAGON
        self.account.hunt = Hunt(area_id="deep_dragon", name="Deep Dragon", max_hit=max_hit)
        self.last_hunt_start_time = time.time()

        logging.info(f"Deep Dragon started for {self.account.username}. Timer set for {self.DURATION}s.")

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
        if self.last_hunt_start_time > 0 and (time.time() - self.last_hunt_start_time >= self.DURATION):
            logging.info(f"Deep Dragon timer finished for {self.account.username}. Claiming and restarting.")
            self._claim_rewards()
            self.pub_service.regenerate(sleep=False)
            self.hunt()
            return

        response = self.account.session.get(DEEP_DRAGON_URL)
        response.raise_for_status()

        current_health, max_health = self._parse_current_health(response.text)
        potion_count = self._parse_potion_count(response.text)

        if potion_count < 5:
            logging.info(f"Potion count low ({potion_count}) for {self.account.username}. Buying more.")
            self._buy_potions()

        if self.account.stats.health <= self.account.hunt.max_hit * 2:
            logging.info(f"Low health ({current_health}) detected for {self.account.username}. Using potion.")
            self._use_potion()

    def _claim_rewards(self) -> None:
        logging.info(f"Claiming Deep Dragon rewards for {self.account.username}")
        try:
            response = self.account.session.get(DEEP_DRAGON_URL)
            csrf = self._get_csrf(response.text)

            self.account.session.post(
                DEEP_DRAGON_URL,
                data={
                    "csrf_token": csrf,
                    "action": "claim"
                },
                headers={
                    "referer": DEEP_DRAGON_URL,
                    "origin": BASE_URL,
                    "content-type": "application/x-www-form-urlencoded"
                }
            ).raise_for_status()

            logging.info(f"Successfully claimed rewards for {self.account.username}")
        except Exception as e:
            logging.error(f"Failed to claim rewards for {self.account.username}: {e}")

    def _parse_current_health(self, html: str) -> tuple[int, int]:
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

    def _parse_potion_count(self, html: str) -> int:
        soup = BeautifulSoup(html, "html.parser")
        button = soup.find("button", string=re.compile(r"USE LIFE POTION"))
        if button:
            match = re.search(r"\((\d+)\)", button.get_text())
            if match:
                return int(match.group(1))
        return 0

    def _buy_potions(self) -> None:
        try:
            response = self.account.session.get(DEEP_DRAGON_URL)
            csrf = self._get_csrf(response.text)

            self.account.session.post(
                DEEP_DRAGON_URL,
                data={
                    "csrf_token": csrf,
                    "action": "buy_potion",
                    "qty": "1"
                },
                headers={
                    "referer": DEEP_DRAGON_URL,
                    "origin": BASE_URL,
                    "content-type": "application/x-www-form-urlencoded"
                }
            ).raise_for_status()

            logging.info(f"Successfully bought a potion for {self.account.username}")
        except Exception as e:
            logging.error(f"Failed to buy potion for {self.account.username}: {e}")

    def _use_potion(self) -> None:
        try:
            response = self.account.session.get(DEEP_DRAGON_URL)
            csrf = self._get_csrf(response.text)

            self.account.session.post(
                DEEP_DRAGON_URL,
                data={
                    "csrf_token": csrf,
                    "action": "use_potion"
                },
                headers={
                    "referer": DEEP_DRAGON_URL,
                    "origin": BASE_URL,
                    "content-type": "application/x-www-form-urlencoded"
                }
            ).raise_for_status()

            logging.info(f"Potion used successfully for {self.account.username}")
        except Exception as e:
            logging.error(f"Failed to use potion for {self.account.username}: {e}")

    def stop_hunt(self) -> None:
        logging.info(f"Stopping Deep Dragon hunt for {self.account.username}")

        response = self.account.session.get(DEEP_DRAGON_URL)
        response.raise_for_status()
        csrf = self._get_csrf(response.text)

        self.account.session.post(
            DEEP_DRAGON_URL,
            data={
                "csrf_token": csrf,
                "action": "escape"
            },
            headers={
                "referer": DEEP_DRAGON_URL,
                "origin": BASE_URL,
                "content-type": "application/x-www-form-urlencoded"
            }
        ).raise_for_status()

        self.account.hunt = None
        self.account.mode = Mode.IDLE

        logging.info(f"Successfully escaped Deep Dragon for {self.account.username}")

    def _get_csrf(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        csrf_input = soup.find("input", {"type": "hidden", "name": "csrf_token"})
        if csrf_input:
            return csrf_input.get("value", "")
        return ""
