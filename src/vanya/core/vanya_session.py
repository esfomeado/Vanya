import logging
import time

from curl_cffi import Session
from curl_cffi.requests.exceptions import HTTPError


class VanyaSession:
    def __init__(self, session: Session, login_callback):
        self._session = session
        self._login_callback = login_callback
        self._max_retries = 3

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

                if response.status_code == 302 and "Unauthorized" in response.text:
                    logging.info("Session expired (302 with Unauthorized), logging in again")
                    self._login_callback()
                    continue

                return response
            except HTTPError as e:
                last_exception = e
                if e.response is not None and e.response.status_code in (401, 403):
                    logging.info("Session expired, logging in again")
                    self._login_callback()
                    continue
                time.sleep(1 * attempt)
            except Exception as e:
                last_exception = e
                time.sleep(1 * attempt)

        raise last_exception

    def __getattr__(self, name):
        return getattr(self._session, name)
