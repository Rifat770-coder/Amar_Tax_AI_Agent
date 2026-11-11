from pathlib import Path
from unittest.mock import patch

import pytest

from amar_tax.database import load_database
from amar_tax.models import Profile
from amar_tax.service import describe_ai_failure, generate_crew_report


def test_quota_message_is_safe():
    status = describe_ai_failure(RuntimeError("credit_balance_exhausted secret-key-do-not-show"))
    assert not status.connected
    assert "credits" in status.detail
    assert "secret-key" not in status.detail


def test_unavailable_model_gives_actionable_message():
    issue = describe_ai_failure(RuntimeError("400: Upstream request failed: Model is unavailable."))
    assert not issue.connected
    assert "AMAR_TAX_MODEL" in issue.detail


def test_missing_key_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    root = Path(__file__).resolve().parents[1]
    p = Profile.model_validate_json((root / "examples/01_example.json").read_text())
    db, source = load_database()
    report, issue = generate_crew_report(p, db, source)
    assert issue is not None
    assert report.calculation.net_tax == 110000
    assert report.review.status == "Flagged"
    assert report.mode.startswith("offline fallback")


def test_provider_quota_fallback_and_no_repeated_requests(monkeypatch):
    pytest.importorskip("crewai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    root = Path(__file__).resolve().parents[1]
    p = Profile.model_validate_json((root / "examples/01_example.json").read_text())
    db, source = load_database()
    with patch("amar_tax.service.run_crew_bounded", side_effect=RuntimeError("credit_balance_exhausted")) as crew:
        report, issue = generate_crew_report(p, db, source)
        again, same_issue = generate_crew_report(p, db, source, issue)
        assert crew.call_count == 1
    assert report.calculation.net_tax == again.calculation.net_tax == 110000
    assert same_issue == issue
    assert report.review.status == "Flagged"
