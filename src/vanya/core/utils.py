import re

from src.vanya.core.errors import VanyaError


def get_global_csrf(html: str) -> str:
    match = re.search(r'globalCsrfToken\s*=\s*"([a-f0-9]+)"', html)
    if not match:
        raise VanyaError("Global CSRF token not found")
    return match.group(1)
