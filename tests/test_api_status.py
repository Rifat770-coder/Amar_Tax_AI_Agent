import json
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from amar_tax.api_status import check_api_connection

BASE = "https://api.openai.com/v1"


def test_missing_key_never_calls_api():
    with patch("amar_tax.api_status.urlopen") as request:
        assert not check_api_connection("", "openai/gpt-4o-mini", BASE).connected
        request.assert_not_called()


def test_authenticated_model_probe():
    with patch("amar_tax.api_status.urlopen") as request:
        request.return_value.__enter__.return_value.read.return_value = json.dumps(
            {"id":"gpt-4o-mini", "object":"model"}).encode()
        assert check_api_connection("test-only", "openai/gpt-4o-mini", BASE).connected
        args, kwargs = request.call_args
        assert args[0].full_url == BASE + "/models/gpt-4o-mini"
        assert args[0].get_method() == "GET"
        assert args[0].data is None
        assert args[0].get_header("User-agent") == "AmarTax/1.0"
        assert kwargs["timeout"] == 5


@pytest.mark.parametrize("error", [HTTPError(BASE, code, "error", None, None) for code in (401,403,404,429,500)] + [OSError("secret must never appear")])
def test_failed_probe_is_red_without_leaking_errors(error):
    with patch("amar_tax.api_status.urlopen", side_effect=error):
        status = check_api_connection("test-only", "openai/gpt-4o-mini", BASE)
    assert not status.connected
    assert "secret" not in status.detail


def test_invalid_response_is_not_connected():
    with patch("amar_tax.api_status.urlopen") as request:
        request.return_value.__enter__.return_value.read.return_value = b'{}'
        assert not check_api_connection("test-only", "openai/gpt-4o-mini", BASE).connected
