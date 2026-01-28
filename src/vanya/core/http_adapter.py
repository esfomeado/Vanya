from requests.adapters import HTTPAdapter
from urllib3 import Retry


class VanyaHttpAdapter(HTTPAdapter):
    MAX_POOL_CONNECTIONS = 1
    MAX_RETRIES = 3
    TIMEOUT = 15

    def __init__(self, **kwargs):
        retries = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1
        )

        super().__init__(max_retries=retries, pool_connections=self.MAX_POOL_CONNECTIONS, pool_maxsize=self.MAX_POOL_CONNECTIONS, **kwargs)

    def send(self, request, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.TIMEOUT
        return super().send(request, **kwargs)
