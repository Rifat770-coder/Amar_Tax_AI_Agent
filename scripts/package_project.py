"""Package source and submission evidence; exclude environments and caches."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
folders = ["amar_tax", "tests", "examples", "docs", "scripts", "evidence", ".streamlit", ".github"]
top = ["README.md", "SECURITY.md", "pyproject.toml", "uv.lock", "render.yaml", ".python-version", ".env.example", ".gitignore", "app.py", "start.bat"]
paths = [root / name for name in top]
for folder in folders:
    paths.extend(p for p in (root / folder).rglob("*") if p.is_file()
                 and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".log", ".db", ".sqlite", ".sqlite3"}
                 and not p.name.startswith(".env") and p.name != "secrets.toml")
archive = root / "Amar-Tax-Submission.zip"
with ZipFile(archive, "w", ZIP_DEFLATED) as output:
    for path in sorted(paths):
        if path.exists():
            output.write(path, path.relative_to(root))
print(f"Created {archive.name}: {archive.stat().st_size:,} bytes")
