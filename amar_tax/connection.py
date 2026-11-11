"""Validated server-side OpenAI-compatible connection settings."""
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ConnectionConfig:
    base_url: str
    model: str
    api_key: str = field(repr=False)

    def __post_init__(self):
        base = self.base_url.strip().rstrip("/")
        model = self.model.strip()
        key = self.api_key.strip()
        parsed = urlsplit(base)
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("সঠিক Base URL দিন; URL-এ key, username বা query parameter দেবেন না।")
        if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")):
            raise ValueError("HTTPS Base URL দিন। Localhost-এর জন্য HTTP ব্যবহার করা যাবে।")
        if not model or any(c in model for c in "\r\n"):
            raise ValueError("আপনার API-তে পাওয়া যায় এমন সঠিক Model ID লিখুন।")
        if not key or any(c in key for c in "\r\n"):
            raise ValueError("Custom provider-এর API key দিন।")
        object.__setattr__(self, "base_url", base)
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "api_key", key)


def server_connection() -> ConnectionConfig | None:
    """An explicit base URL selects a custom OpenAI-compatible provider."""
    base = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
    if not base:
        return None
    return ConnectionConfig(base, os.getenv("AMAR_TAX_MODEL", "openai/gpt-4o-mini"),
                            os.getenv("OPENAI_API_KEY", ""))
