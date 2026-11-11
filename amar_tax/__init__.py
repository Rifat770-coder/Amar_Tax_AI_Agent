"""Amar Tax: simulated assignment rules, never real tax advice."""
import os
from pathlib import Path

# CrewAI imports create storage even when memory is disabled. Keep it in the project.
os.environ.setdefault("CREWAI_STORAGE_DIR", str(Path.cwd() / ".crewai-storage"))
os.environ.setdefault("CREWAI_TELEMETRY_DISABLED", "true")
