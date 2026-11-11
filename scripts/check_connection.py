"""Check configured API access without printing credentials or taxpayer data."""
import os

from amar_tax.api_status import check_api_connection
from amar_tax.settings import load_project_env

load_project_env()
status = check_api_connection(
    os.getenv("OPENAI_API_KEY", ""),
    os.getenv("AMAR_TAX_MODEL", "openai/gpt-4o-mini"),
    os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1",
)
print("API connected" if status.connected else "API not connected")
print(status.detail)
