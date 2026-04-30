import os
import sys

import yaml

from src.vanya.core.errors import VanyaError
from src.vanya.model.config import Config


def _get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()


def load_config() -> Config:
    path = os.path.join(_get_app_dir(), "accounts.yaml")
    if not os.path.exists(path):
        raise VanyaError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Config(**raw)


CONFIG: Config = load_config()
