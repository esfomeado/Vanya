import logging
import random
import time

from curl_cffi import Session
from curl_cffi.requests.exceptions import HTTPError

from src.vanya.core.constants import BASE_URL
from src.vanya.core.demona_shield import (
    DemonaShieldError,
    DemonaShieldLocked,
    is_shield_challenge,
    parse_shield,
)


class VanyaSession:
    def __init__(self, session: Session, login_callback):
        self._session = session
        self._login_callback = login_callback
        self._max_retries = 3
        self._is_logging_in = False
        self._is_solving_shield = False

    def get(self, *args, **kwargs):
        return self.request("GET", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request("POST", *args, **kwargs)

    def request(self, method, *args, **kwargs):
        last_exception = None
        for attempt in range(self._max_retries):
            try:
                response = self._session.request(method, *args, **kwargs)
                response.raise_for_status()

                if response.url.lower().startswith(f"{BASE_URL}/index?error"):
                    if not self._is_logging_in:
                        logging.info("Session expired, logging in again")
                        self._trigger_login()
                        continue
                    return response

                if self._should_solve_shield(response):
                    self._solve_shield(response)
                    continue

                return response
            except HTTPError as e:
                last_exception = e
                if e.response is not None and e.response.status_code in (401, 403):
                    if not self._is_logging_in:
                        logging.info("Session expired, logging in again")
                        self._trigger_login()
                        continue
                time.sleep(1 * attempt)
            except Exception as e:
                last_exception = e
                time.sleep(1 * attempt)

        if last_exception is not None:
            raise last_exception
        raise RuntimeError(f"Request to {args[0] if args else '?'} exhausted retries")

    def _should_solve_shield(self, response) -> bool:
        if self._is_solving_shield:
            return False
        content_type = (response.headers.get("content-type") or "").lower()
        if "html" not in content_type:
            return False
        try:
            return is_shield_challenge(response.text)
        except Exception:
            return False

    def _solve_shield(self, response) -> None:
        self._is_solving_shield = True
        try:
            shield_url = str(response.url)
            try:
                post_url, data = parse_shield(shield_url, response.text)
            except DemonaShieldLocked as e:
                logging.warning(f"Demona Shield locked for {e.seconds}s, sleeping")
                time.sleep(e.seconds + 1)
                return
            except DemonaShieldError as e:
                logging.error(f"Demona Shield parse error: {e}")
                return

            submitted_token = data.get("human_token")
            submitted_answer = data.get("human_answer")
            logging.info(
                f"Demona Shield detected at {shield_url}, submitting "
                f"token={submitted_token} answer={submitted_answer} -> {post_url}"
            )

            time.sleep(random.uniform(3.0, 7.0))

            try:
                shield_response = self._session.post(
                    post_url,
                    data=data,
                    headers={
                        "content-type": "application/x-www-form-urlencoded",
                        "referer": shield_url,
                        "origin": BASE_URL,
                    },
                )
            except HTTPError as e:
                logging.error(f"Demona Shield submit failed: {e}")
                return

            if is_shield_challenge(shield_response.text):
                try:
                    parse_shield(str(shield_response.url), shield_response.text)
                except DemonaShieldLocked as e:
                    logging.warning(
                        f"Demona Shield locked after rejection for {e.seconds}s "
                        f"(rejected token={submitted_token} answer={submitted_answer}), "
                        f"sleeping"
                    )
                    time.sleep(e.seconds + 1)
                    return
                except DemonaShieldError:
                    pass
                logging.error(
                    f"Demona Shield verification rejected the answer "
                    f"(token={submitted_token} answer={submitted_answer})"
                )
                return

            logging.info(
                f"Demona Shield cleared (token={submitted_token} answer={submitted_answer})"
            )
        finally:
            self._is_solving_shield = False

    def _trigger_login(self):
        self._is_logging_in = True
        try:
            self._login_callback()
        finally:
            self._is_logging_in = False

    def __getattr__(self, name):
        return getattr(self._session, name)
