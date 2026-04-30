from typing import TypeVar


class ServiceRegistry:
    T = TypeVar('T')

    def __init__(self):
        self._services: dict[tuple[type, str], object] = {}

    def get(self, service_cls: type[T], account) -> T:
        key = (service_cls, account.username)
        if key not in self._services:
            self._services[key] = service_cls(account)
        return self._services[key]


service_registry = ServiceRegistry()
