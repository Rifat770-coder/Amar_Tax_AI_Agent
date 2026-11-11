"""Reload project-local .env settings without exposing credential values."""
import os
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ENV = Path(__file__).resolve().parents[1] / ".env"
SETTING_KEYS = ("OPENAI_API_KEY", "AMAR_TAX_MODEL", "OPENAI_BASE_URL", "OPENAI_API_BASE", "AMAR_TAX_RULES_URL", "AMAR_TAX_CREW_TIMEOUT", "AMAR_TAX_APP_PASSWORD")


class EnvLoader:
    def __init__(self):
        self.original = {}
        self.managed = set()

    def load(self, path: Path = PROJECT_ENV) -> None:
        values = dotenv_values(path, encoding="utf-8-sig", interpolate=False) if path.is_file() else {}
        for key in SETTING_KEYS:
            if key in values:
                if key not in self.managed:
                    self.original[key] = os.environ.get(key)
                os.environ[key] = values[key] or ""
                self.managed.add(key)
            elif key in self.managed:
                original = self.original.pop(key)
                if original is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original
                self.managed.remove(key)


_loader = EnvLoader()


def load_project_env() -> None:
    """The project's .env overrides matching shell values; removing it restores them."""
    _loader.load()
