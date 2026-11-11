import json
import os
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from amar_tax.api_status import check_api_connection
from amar_tax.connection import ConnectionConfig
from amar_tax.database import load_database
from amar_tax.engine import run_offline
from amar_tax.models import Profile
from amar_tax.service import generate_crew_report


def test_custom_config_normalizes_without_revealing_key():
    config = ConnectionConfig(" https://proxy.example/v1/ ", " org/model ", " private-test-key ")
    assert config.base_url == "https://proxy.example/v1"
    assert config.model == "org/model"
    assert config.api_key == "private-test-key"
    assert "private-test-key" not in repr(config)


@pytest.mark.parametrize("url", ["", "ftp://example.test/v1", "https://user:pass@example.test/v1", "https://example.test/v1?key=secret"])
def test_bad_endpoint_rejected(url):
    with pytest.raises(ValueError):
        ConnectionConfig(url, "model", "test-key")


def test_proxy_models_list_fallback():
    response = json.dumps({"data":[{"id":"org/model"}]}).encode()
    with patch("amar_tax.api_status.urlopen") as request:
        context = request.return_value
        context.__enter__.return_value.read.return_value = response
        request.side_effect = [HTTPError("https://proxy.example/v1/models/org%2Fmodel",404,"missing",None,None), context]
        assert check_api_connection("proxy-key", "org/model", "https://proxy.example/v1").connected
        assert request.call_args_list[1].args[0].full_url == "https://proxy.example/v1/models"


def test_custom_settings_forwarded_without_mutating_environment(monkeypatch):
    pytest.importorskip("crewai")
    monkeypatch.setenv("OPENAI_API_KEY", "original-key")
    p = Profile.model_validate_json((Path(__file__).resolve().parents[1] / "examples/01_example.json").read_text())
    db, source = load_database()
    config = ConnectionConfig("https://proxy.example/v1", "org/model", "proxy-key")
    with patch("amar_tax.service.run_crew_bounded", return_value=(run_offline(p, db, source), None)) as crew:
        _, issue = generate_crew_report(p, db, source, config=config)
        assert crew.call_args.kwargs["config"] is config
    assert issue is None
    assert os.environ["OPENAI_API_KEY"] == "original-key"


def test_custom_server_settings_and_no_credential_form(monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from amar_tax.api_status import APIStatus

    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "proxy-test-key")
    monkeypatch.setenv("AMAR_TAX_MODEL", "org/model")
    with patch("amar_tax.settings.load_project_env"), \
         patch("amar_tax.api_status.check_api_connection", return_value=APIStatus(True,"Connected")) as probe, \
         patch("amar_tax.service.generate_crew_report") as generate:
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        app.radio[0].set_value("CrewAI · AI agents").run()
        app.button(key="nav_profile").click().run()
        assert not app.exception
        assert [x.label for x in app.text_input] == ["পেশা / Profession"]
        assert not any(x.label == "API provider" for x in app.selectbox)
        assert probe.call_args.args == ("proxy-test-key", "org/model", "https://proxy.example/v1")
        def respond(profile, db, source, known_issue=None, config=None):
            from amar_tax.connection import server_connection
            server = server_connection()
            assert server.model == "org/model"
            assert server.api_key == "proxy-test-key"
            return run_offline(profile, db, source), None
        generate.side_effect = respond
        next(b for b in app.button if "রিপোর্ট তৈরি" in b.label).click().run()
        assert not app.exception
        assert app.session_state.report.calculation.net_tax == 110000
        assert "proxy-test-key" not in app.session_state.report.model_dump_json()


def test_service_uses_custom_server_connection(monkeypatch):
    pytest.importorskip("crewai")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "server-test-key")
    monkeypatch.setenv("AMAR_TAX_MODEL", "org/model")
    p = Profile.model_validate_json((Path(__file__).resolve().parents[1] / "examples/01_example.json").read_text())
    db, source = load_database()
    with patch("amar_tax.service.run_crew_bounded", return_value=(run_offline(p, db, source), None)) as crew:
        report, issue = generate_crew_report(p, db, source)
        assert crew.call_args.kwargs["config"].base_url == "https://proxy.example/v1"
        assert crew.call_args.kwargs["config"].model == "org/model"
    assert issue is None
    assert report.calculation.net_tax == 110000
