from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


def test_public_server_opens_without_password(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("AMAR_TAX_APP_PASSWORD", raising=False)
    with patch("amar_tax.settings.load_project_env"), patch("amar_tax.api_status.check_api_connection") as api:
        app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert app.session_state.current_view == "Dashboard"
    assert not any(field.key == "access_password" for field in app.text_input)


def test_access_code_and_rotation(monkeypatch):
    monkeypatch.setenv("AMAR_TAX_APP_PASSWORD", "test-access-only")
    with patch("amar_tax.settings.load_project_env"):
        app = AppTest.from_file(str(APP)).run()
        app.text_input(key="access_password").set_value("wrong")
        next(b for b in app.button if b.label == "Open dashboard").click().run()
        assert len(app.error) == 1
        assert len(app.radio) == 0
        app.text_input(key="access_password").set_value("test-access-only")
        next(b for b in app.button if b.label == "Open dashboard").click().run()
        assert not app.exception
        assert app.session_state.current_view == "Dashboard"
        assert "access_password" not in app.session_state
        assert app.session_state.access_granted != "test-access-only"
        monkeypatch.setenv("AMAR_TAX_APP_PASSWORD", "rotated-test-access")
        app.run()
        assert len(app.radio) == 0
        assert len(app.text_input) == 1
