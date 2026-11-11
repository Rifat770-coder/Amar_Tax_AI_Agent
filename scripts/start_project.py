"""Windows launcher helper: prepare dependencies and open the local UI."""
import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8501"


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Amar Tax locally")
    parser.add_argument("--check", action="store_true", help="Check readiness without launching a server")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open a browser")
    parser.add_argument("--reuse", action="store_true", help="Reuse a running server instead of restarting it")
    args = parser.parse_args()
    os.chdir(ROOT)
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        print("Python 3.11, 3.12 or 3.13 is required.")
        return 1
    required = ("streamlit", "crewai", "pydantic", "dotenv", "amar_tax")
    missing = [name for name in required if importlib.util.find_spec(name) is None]
    if missing:
        if args.check:
            print("Missing dependencies: " + ", ".join(missing))
            return 1
        print("Installing required packages. First setup needs internet...", flush=True)
        uv = shutil.which("uv")
        if uv:
            command = [uv, "--cache-dir", str(ROOT / ".uv-cache"), "sync", "--locked", "--extra", "ui", "--extra", "crew"]
        else:
            if importlib.util.find_spec("pip") is None:
                subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True)
            command = [sys.executable, "-m", "pip", "install", "-e", ".[ui,crew]"]
        subprocess.run(command, cwd=ROOT, check=True)
    if args.check:
        print("READY: Amar Tax UI and CrewAI dependencies are installed.")
        print("Server settings: .env " + ("found" if (ROOT / ".env").is_file() else "not configured; offline mode is available"))
        return 0
    try:
        with urlopen(URL + "/_stcore/health", timeout=2) as response:
            running = response.status == 200 and response.read(32).strip() == b"ok"
    except OSError:
        running = False
    if running and not args.reuse:
        print("Restarting the project server to load the latest code...", flush=True)
        subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(ROOT / "scripts" / "stop_project_server.ps1")], check=True)
        for _ in range(15):
            try:
                with urlopen(URL + "/_stcore/health", timeout=1):
                    pass
            except OSError:
                running = False
                break
            time.sleep(0.2)
        if running:
            print("Port 8501 is still occupied. An unrelated server was left untouched.")
            return 1
    if running:
        print("Amar Tax is already running: " + URL)
        if not args.no_browser:
            webbrowser.open(URL)
        return 0
    print("Starting Amar Tax: " + URL, flush=True)
    print("Keep this window open. Press Ctrl+C to stop the server.", flush=True)
    try:
        return subprocess.call([sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
            "--server.address=127.0.0.1", "--server.port=8501",
            "--server.fileWatcherType=poll", "--server.runOnSave=true",
            "--server.headless=" + ("true" if args.no_browser else "false")], cwd=ROOT)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError):
        print("Startup failed. Check your internet connection and dependency installation.")
        raise SystemExit(1)
