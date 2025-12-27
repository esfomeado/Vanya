import os

import yaml

from src.vanya.core.errors import VanyaError
from src.vanya.model.config import Config

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))


def load_config() -> Config:
    path = os.path.join(PROJECT_ROOT, "accounts.yaml")
    if not os.path.exists(path):
        raise VanyaError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Config(**raw)


CONFIG: Config = load_config()
