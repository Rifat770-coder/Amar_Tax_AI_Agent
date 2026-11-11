"""Run the public assignment example through bounded AI/fallback generation."""
import time
import argparse
from pathlib import Path

from amar_tax.database import load_database
from amar_tax.models import Profile
from amar_tax.report import render_markdown
from amar_tax.service import generate_crew_report
from amar_tax.settings import load_project_env

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--gender", choices=["male", "female", "other"])
parser.add_argument("--ui-profile", action="store_true")
parser.add_argument("--output", type=Path, default=root / "evidence/provider_check_report.md")
args = parser.parse_args()
load_project_env()
profile = Profile.model_validate_json((root / "examples/01_example.json").read_text())
data = profile.model_dump()
if args.gender:
    data["gender"] = args.gender
if args.ui_profile:
    present = {source["kind"] for source in data["income_sources"]}
    data["income_sources"].extend({"kind":kind,"amount":0} for kind in ("salaried","freelancer","business","landlord","investor","other") if kind not in present)
profile = Profile.model_validate(data)
db, source = load_database()
started = time.monotonic()
report, issue = generate_crew_report(profile, db, source)
print(f"Completed in {time.monotonic() - started:.1f}s")
print("Mode:", report.mode)
print("Net payable:", report.calculation.net_tax)
print("Report status:", report.review.status)
target = args.output
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(render_markdown(report, db), encoding="utf-8")
target.with_suffix(".json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
print("Saved:", target.name)
