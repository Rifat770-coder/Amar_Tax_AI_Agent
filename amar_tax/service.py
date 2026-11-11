"""Keep tax reports available when the optional AI provider is unavailable."""
import os

from .api_status import APIStatus
from .engine import run_offline
from .connection import ConnectionConfig, server_connection
from .runner import run_crew_bounded


def describe_ai_failure(exc: Exception) -> APIStatus:
    # Inspect locally, but never return raw provider messages, keys or profile data.
    messages = []
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current).lower())
        current = current.__cause__ or current.__context__
    text = " ".join(messages)
    if any(code in text for code in ("credit_balance_exhausted", "insufficient_quota", "no credits remaining")):
        return APIStatus(False, "OpenAI API credits শেষ বা quota অতিক্রম হয়েছে। API Billing থেকে credit যোগ করুন, তারপর আবার যাচাই করে রিপোর্ট তৈরি করুন।")
    if any(code in text for code in ("401", "authentication", "invalid_api_key")):
        return APIStatus(False, "API key গ্রহণ করা হয়নি। .env-এর key ও account permissions পরীক্ষা করুন।")
    if "429" in text or "rate_limit" in text:
        return APIStatus(False, "API request limit অতিক্রম হয়েছে। কিছুক্ষণ পরে আবার যাচাই করুন।")
    if any(code in text for code in ("404", "not_found", "not found", "model is unavailable", "model is not supported")):
        return APIStatus(False, "নির্বাচিত model দিয়ে generation করা যাচ্ছে না। .env-এর AMAR_TAX_MODEL-এ provider-এর কার্যকর Model ID দিন।")
    if "503" in text or "502" in text:
        return APIStatus(False, "API provider-এর model service সাময়িকভাবে অনুপলব্ধ। পরে আবার যাচাই করুন।")
    if "timeout" in text or "timed out" in text:
        return APIStatus(False, "API উত্তর দিতে বেশি সময় নিচ্ছে। পরে আবার যাচাই করুন।")
    return APIStatus(False, "AI রিপোর্ট তৈরি হয়নি। সংযোগ, model access ও server configuration পরীক্ষা করে আবার চেষ্টা করুন।")


def offline_fallback(profile, db, source, issue: APIStatus):
    report = run_offline(profile, db, source)
    report.mode = "offline fallback (CrewAI unavailable; Local DB calculation)"
    report.review.status = "Flagged"
    report.review.findings.append("AI unavailable: " + issue.detail)
    report.review.findings.append("Report generated using the Local DB deterministic fallback; no successful AI generation is claimed.")
    return report, issue


def generate_crew_report(profile, db, source, known_issue: APIStatus | None = None,
                         config: ConnectionConfig | None = None):
    if known_issue is not None:
        return offline_fallback(profile, db, source, known_issue)
    if config is None and not os.getenv("OPENAI_API_KEY", "").strip():
        return offline_fallback(profile, db, source, APIStatus(False, "সার্ভারে OPENAI_API_KEY সেট করা নেই।"))
    try:
        if config is None:
            config = server_connection()
        report, issue = run_crew_bounded(profile, db, source, config=config)
        if issue is not None:
            return offline_fallback(profile, db, source, issue)
        return report, None
    except Exception as exc:
        return offline_fallback(profile, db, source, describe_ai_failure(exc))
