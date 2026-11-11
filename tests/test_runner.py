import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from amar_tax.database import load_database
from amar_tax.engine import run_offline
from amar_tax.models import Profile
from amar_tax.runner import crew_timeout, run_crew_bounded


def inputs():
    p = Profile.model_validate_json((Path(__file__).resolve().parents[1] / "examples/01_example.json").read_text())
    db, source = load_database()
    return p, db, source


def test_timeout_stops_worker_and_reports_failure():
    process = MagicMock(pid=12345)
    process.communicate.side_effect = [subprocess.TimeoutExpired("worker", 60), ("", "")]
    with patch("amar_tax.runner.subprocess.Popen", return_value=process), \
         patch("amar_tax.runner.subprocess.run") as stop_tree:
        report, issue = run_crew_bounded(*inputs())
    assert report is None
    assert not issue.connected
    assert "সময়সীমা" in issue.detail
    assert process.communicate.call_count == 2
    import os
    if os.name == "nt":
        assert stop_tree.call_args.args[0] == ["taskkill", "/PID", "12345", "/T", "/F"]
    else:
        process.kill.assert_called_once()


def test_worker_success_is_validated():
    p, db, source = inputs()
    expected = run_offline(p, db, source)
    process = MagicMock(returncode=0)
    result_paths = []
    def spawn_worker(command, **kwargs):
        result_path = Path(command[-1])
        result_paths.append(result_path)
        def communicate(*args, **kwargs):
            result_path.write_text(json.dumps({"report":expected.model_dump(mode="json")}), encoding="utf-8")
            # Real CrewAI background logs can appear both before and after result output.
            return ("Crew completed!\n{not valid JSON}\nLate trace log", "Verbose log")
        process.communicate.side_effect = communicate
        return process
    with patch("amar_tax.runner.subprocess.Popen", side_effect=spawn_worker) as spawn:
        report, issue = run_crew_bounded(p, db, source)
    assert issue is None
    assert report == expected
    assert spawn.call_args.kwargs["env"]["PYTHONIOENCODING"] == "utf-8"
    assert Path(spawn.call_args.kwargs["env"]["CREWAI_STORAGE_DIR"]).parent == result_paths[0].parent
    assert not result_paths[0].exists()


def test_real_invalid_report_is_still_rejected():
    process = MagicMock(returncode=0)
    def spawn_worker(command, **kwargs):
        def communicate(*args, **kwargs):
            Path(command[-1]).write_text('{"report":{"mode":"CrewAI"}}', encoding="utf-8")
            return ("", "")
        process.communicate.side_effect = communicate
        return process
    with patch("amar_tax.runner.subprocess.Popen", side_effect=spawn_worker):
        report, issue = run_crew_bounded(*inputs())
    assert report is None
    assert not issue.connected


def test_timeout_setting_is_bounded(monkeypatch):
    for value, expected in [("5",10),("9999",180),("bad",60),("45",45)]:
        monkeypatch.setenv("AMAR_TAX_CREW_TIMEOUT", value)
        assert crew_timeout() == expected
