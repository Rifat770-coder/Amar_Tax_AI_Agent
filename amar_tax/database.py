"""Remote availability is optional; the assignment DB always controls rules."""
import json
import logging
from importlib.resources import files
from urllib.request import urlopen

log = logging.getLogger(__name__)


def load_database(remote_url: str | None = None) -> tuple[dict, str]:
    local = json.loads(files("amar_tax").joinpath("data/tax_db.json").read_text(encoding="utf-8"))
    if remote_url:
        try:
            with urlopen(remote_url, timeout=5) as response:
                raw = response.read(1_000_001)
            if len(raw) > 1_000_000:
                raise ValueError("Rules response is too large")
            remote = json.loads(raw)
            if remote != local:
                raise ValueError("Remote rules differ from the assignment source of truth")
            return local, "Remote verified against local assignment DB"
        except (OSError, ValueError) as exc:
            log.warning("Rules API failed (%s); falling back to Local DB", type(exc).__name__)
    log.info("Using Local DB (simulated assignment rules)")
    return local, "Local DB (simulated 2026-27)"
