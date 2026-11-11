"""Isolated AI worker; credentials arrive over stdin, report uses a separate channel."""
import contextlib
import json
import sys
from pathlib import Path


def main(result_path: Path | None = None):
    from .connection import ConnectionConfig
    from .models import Profile
    from .service import describe_ai_failure

    payload = json.load(sys.stdin)
    try:
        # Keep verbose CrewAI output separate from the machine-readable result.
        with contextlib.redirect_stdout(sys.stderr):
            from .crew import run_crew
            profile = Profile.model_validate(payload["profile"])
            config = ConnectionConfig(**payload["config"]) if payload.get("config") else None
            report = run_crew(profile, payload["db"], payload["source"], config=config)
        result = {"report": report.model_dump(mode="json")}
    except Exception as exc:
        result = {"error": describe_ai_failure(exc).detail}
    encoded = json.dumps(result, ensure_ascii=False)
    if result_path is not None:
        # Verbose/background agent logs may write to stdout after the redirect ends.
        # A dedicated result channel keeps those logs out of the report protocol.
        result_path.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-path", type=Path)
    args = parser.parse_args()
    main(args.result_path)
