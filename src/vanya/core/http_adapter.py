from requests.adapters import HTTPAdapter
from urllib3 import Retry


class VanyaHttpAdapter(HTTPAdapter):
    MAX_RETRIES = 3
    TIMEOUT = 10

    def __init__(self, **kwargs):
        retries = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=0.3
        )

        super().__init__(max_retries=retries, **kwargs)

    def send(self, request, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.TIMEOUT
        return super().send(request, **kwargs)
