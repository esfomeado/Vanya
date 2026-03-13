import logging
import time

from curl_cffi import Session
from curl_cffi.requests.exceptions import HTTPError

from src.vanya.core.constants import BASE_URL


class VanyaSession:
    def __init__(self, session: Session, login_callback):
        self._session = session
        self._login_callback = login_callback
        self._max_retries = 3
        self._is_logging_in = False

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

        raise last_exception

    def _trigger_login(self):
        self._is_logging_in = True
        try:
            self._login_callback()
        finally:
            self._is_logging_in = False

    def __getattr__(self, name):
        return getattr(self._session, name)
