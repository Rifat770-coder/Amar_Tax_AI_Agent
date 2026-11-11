"""Generate genuine offline sample reports with reproducible evidence."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for source in sorted((root / "examples").glob("*.json")):
    result = subprocess.run([sys.executable, "-m", "amar_tax", str(source),
                             "--output", str(root / "evidence" / (source.stem + ".md"))],
                            cwd=root, capture_output=True, text=True, encoding="utf-8")
    (root / "evidence").mkdir(exist_ok=True)
    (root / "evidence" / (source.stem + ".log")).write_text(
        f"Exit code: {result.returncode}\n" + result.stdout + result.stderr, encoding="utf-8")
    print(f"{source.name}: exit {result.returncode}")
    expected = 2 if "invalid" in source.stem else 0
    if result.returncode != expected:
        raise SystemExit(result.returncode or 1)
