"""Bound the complete crew run and stop timed-out workers, including on Windows."""
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

from .api_status import APIStatus
from .models import Report


def crew_timeout() -> int:
    try:
        return min(180, max(10, int(os.getenv("AMAR_TAX_CREW_TIMEOUT", "60"))))
    except ValueError:
        return 60


def run_crew_bounded(profile, db, source, config=None):
    # Ephemeral report data only. API credentials still travel through stdin.
    with tempfile.TemporaryDirectory(prefix="amar-tax-result-") as directory:
        return _run_worker(profile, db, source, config, Path(directory) / "result.json")


def _run_worker(profile, db, source, config, result_path):
    payload = {"profile":profile.model_dump(mode="json"), "db":db, "source":source,
               "config":asdict(config) if config is not None else None}
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", OTEL_SDK_DISABLED="true",
               CREWAI_STORAGE_DIR=str(result_path.parent / "crew-storage"))
    process = subprocess.Popen([sys.executable, "-m", "amar_tax.crew_worker", "--result-path", str(result_path)],
        cwd=Path(__file__).resolve().parents[1], env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        _output, _logs = process.communicate(json.dumps(payload), timeout=crew_timeout())
    except subprocess.TimeoutExpired:
        # Windows venv launchers can create a child Python; stop the entire owned tree.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            process.kill()
        process.communicate(timeout=5)
        return None, APIStatus(False, "AI রিপোর্ট তৈরির সময়সীমা শেষ হয়েছে। Local DB দিয়ে রিপোর্ট তৈরি করা হয়েছে; পরে API আবার যাচাই করুন।")
    if process.returncode != 0:
        return None, APIStatus(False, "AI worker সম্পন্ন হতে পারেনি। Local DB দিয়ে রিপোর্ট তৈরি করা হয়েছে।")
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(result, dict):
            raise ValueError("Invalid result envelope")
        if "error" in result:
            return None, APIStatus(False, result["error"])
        return Report.model_validate(result["report"]), None
    except OSError:
        return None, APIStatus(False, "AI worker-এর ফলাফল পাওয়া যায়নি। আবার চেষ্টা করুন।")
    except (ValueError, KeyError, TypeError):
        return None, APIStatus(False, "AI worker-এর report যাচাই করা যায়নি। আবার চেষ্টা করুন।")
