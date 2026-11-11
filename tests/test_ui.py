from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def submit_profile(app):
    next(b for b in app.button if b.label == "রিপোর্ট তৈরি করুন →").click().run()


def open_profile(app):
    app.button(key="nav_profile").click().run()


def test_ui_example_and_minor():
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert app.session_state.current_view == "Dashboard"
    app.button(key="create_report").click().run()
    submit_profile(app)
    assert not app.exception
    assert app.session_state.report.calculation.net_tax == 110000
    assert app.session_state.report.review.status == "Passed"
    assert "110,000.00" in app.metric[0].value
    assert len(app.metric) == 4
    assert any("Your tax overview" in item.value for item in app.markdown)
    assert any("Income breakdown" in item.value for item in app.markdown)
    assert any('Salary: ৳ 1,200,000' in item.value for item in app.markdown)
    assert app.session_state.current_view == "Dashboard"
    app.button(key="edit_profile").click().run()
    app.number_input[0].set_value(16)
    app.checkbox[0].uncheck()
    submit_profile(app)
    assert not app.exception
    assert app.session_state.report.review.status == "Flagged"
    assert app.session_state.report.documents.checklist[0] == "TIN Registration"


def test_invalid_submission_clears_previous_report():
    app = AppTest.from_file(str(APP)).run()
    open_profile(app)
    submit_profile(app)
    assert "report" in app.session_state
    open_profile(app)
    app.text_input[0].set_value(" ")
    submit_profile(app)
    assert not app.exception
    assert "report" not in app.session_state
    assert len(app.error) == 1


@pytest.mark.parametrize("connected", [False, True])
def test_crew_connection_indicator(monkeypatch, connected):
    from unittest.mock import patch
    from amar_tax.api_status import APIStatus

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with patch("amar_tax.api_status.check_api_connection", return_value=APIStatus(connected, "Test status")) as probe:
        app = AppTest.from_file(str(APP)).run()
        app.radio[0].set_value("CrewAI · AI agents").run()
        assert not app.exception
        label = "API connected" if connected else "API not connected"
        assert any(label in item.value for item in app.markdown)
        assert probe.call_count == 1
        app.run()
        assert probe.call_count == 1
        next(button for button in app.button if "API" in button.label).click().run()
        assert probe.call_count == 2
        app.radio[0].set_value("Offline · Local DB").run()
        assert not any('role="status"' in item.value for item in app.markdown)


def test_ai_failure_still_displays_report_and_red_status():
    from unittest.mock import patch
    from amar_tax.api_status import APIStatus
    from amar_tax.service import offline_fallback

    def failed_crew(profile, db, source, known_issue=None):
        return offline_fallback(profile, db, source, APIStatus(False, "OpenAI API credits শেষ।"))

    with patch("amar_tax.api_status.check_api_connection", return_value=APIStatus(True, "Connected")), \
         patch("amar_tax.service.generate_crew_report", side_effect=failed_crew):
        app = AppTest.from_file(str(APP)).run()
        app.radio[0].set_value("CrewAI · AI agents").run()
        open_profile(app)
        submit_profile(app)
        assert not app.exception
        assert len(app.error) == 0
        assert app.session_state.report.calculation.net_tax == 110000
        assert app.session_state.report.mode.startswith("offline fallback")
        assert any("AI unavailable" in x.value for x in app.markdown)
        app.run()
        assert any("AI unavailable" in x.value for x in app.markdown)


def test_sidebar_views_use_same_report_and_preserve_submitted_profile():
    app = AppTest.from_file(str(APP)).run()
    assert app.session_state.current_view == "Dashboard"
    assert len(app.number_input) == 0
    app.button(key="create_report").click().run()
    app.number_input[0].set_value(45)
    app.selectbox[0].set_value("male")
    next(w for w in app.number_input if w.label == "বেতন / Salary").set_value(800000.0)
    next(w for w in app.number_input if w.label == "ফ্রিল্যান্সিং / Freelance").set_value(0.0)
    next(w for w in app.number_input if w.label == "মোট বিনিয়োগ / Investment (BDT)").set_value(100000.0)
    submit_profile(app)
    assert not app.exception
    assert app.session_state.current_view == "Dashboard"
    assert app.session_state.report.calculation.net_tax == 25000
    original = app.session_state.report.model_dump_json()
    for slug, view in [("analytics","Income analytics"),("report","Tax report"),
                       ("calculation","Tax calculation"),("documents","Documents checklist"),("dashboard","Dashboard")]:
        app.button(key="nav_"+slug).click().run()
        assert not app.exception
        assert app.session_state.current_view == view
        assert app.session_state.report.model_dump_json() == original
    app.button(key="view_report_net_tax").click().run()
    assert app.session_state.current_view == "Tax report"
    open_profile(app)
    assert app.number_input[0].value == 45
    assert app.selectbox[0].value == "male"
    assert next(w for w in app.number_input if w.label == "বেতন / Salary").value == 800000.0
    assert app.session_state.report.model_dump_json() == original


def test_report_views_guide_first_time_users_to_profile():
    app = AppTest.from_file(str(APP)).run()
    app.button(key="nav_report").click().run()
    assert not app.exception
    assert "report" not in app.session_state
    assert len(app.number_input) == 0
    app.button(key="first_report").click().run()
    assert app.session_state.current_view == "Taxpayer profile"
    assert len(app.number_input) == 8
