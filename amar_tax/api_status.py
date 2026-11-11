"""Read-only connectivity probe; never sends taxpayer data or generates tokens."""
import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request
from .network import safe_urlopen as urlopen


@dataclass(frozen=True)
class APIStatus:
    connected: bool
    detail: str


def check_api_connection(api_key: str, model: str, base_url: str) -> APIStatus:
    if not api_key.strip():
        return APIStatus(False, "সার্ভারে OPENAI_API_KEY সেট করা নেই।")
    model_id = model.removeprefix("openai/")
    try:
        request = Request(base_url.rstrip("/") + "/models/" + quote(model_id, safe=""),
                          headers={"Authorization": "Bearer " + api_key.strip(), "Accept": "application/json",
                                   "User-Agent": "AmarTax/1.0"})
        try:
            with urlopen(request, timeout=5) as response:
                data = json.loads(response.read(65537))
        except HTTPError as exc:
            # Many OpenAI-compatible proxies expose only the models list endpoint.
            if exc.code not in (404, 405):
                raise
            list_request = Request(base_url.rstrip("/") + "/models", headers=request.headers)
            with urlopen(list_request, timeout=5) as response:
                listing = json.loads(response.read(1_000_001))
            models = listing.get("data", []) if isinstance(listing, dict) else []
            data = next((item for item in models if isinstance(item, dict) and item.get("id") == model_id), {}) if isinstance(models, list) else {}
            if data.get("id") == model_id:
                data = {**data, "object": "model"}
        if not isinstance(data, dict) or data.get("id") != model_id or data.get("object") != "model":
            return APIStatus(False, "API থেকে প্রত্যাশিত model response পাওয়া যায়নি।")
        return APIStatus(True, "API ও নির্বাচিত মডেলের access যাচাই সফল।")
    except HTTPError as exc:
        if exc.code in (401, 403):
            return APIStatus(False, "API key সঠিক নয় অথবা প্রয়োজনীয় অনুমতি নেই।")
        if exc.code == 404:
            return APIStatus(False, "নির্বাচিত মডেল পাওয়া যায়নি বা access নেই।")
        if exc.code == 429:
            return APIStatus(False, "API limit অতিক্রম হয়েছে; কিছুক্ষণ পরে আবার যাচাই করুন।")
        return APIStatus(False, "API সাড়া দেয়নি; আবার যাচাই করুন।")
    except (OSError, ValueError):
        return APIStatus(False, "API-তে সংযোগ করা যায়নি। ইন্টারনেট ও server configuration পরীক্ষা করুন।")
