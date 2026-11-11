"""Offline pre-upload scan. Report paths/line numbers, never secret contents."""
import re
import subprocess
import tempfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git",".venv",".python",".uv-cache",".crewai-storage","output","__pycache__",".pytest_cache"}
candidate_paths = [ROOT/name for name in ("app.py","start.bat","pyproject.toml","uv.lock","render.yaml","README.md",".gitignore",".env.example",".python-version")]
for folder in ("amar_tax","scripts","tests","docs","examples","evidence",".streamlit",".github"):
    if (ROOT/folder).exists():
        candidate_paths.extend(p for p in (ROOT/folder).rglob("*") if p.is_file() and not any(x in SKIP for x in p.relative_to(ROOT).parts))
values = dotenv_values(ROOT/".env",interpolate=False) if (ROOT/".env").exists() else {}
secrets = [v for k,v in values.items() if v and len(v)>=12 and any(s in k.upper() for s in ("KEY","PASSWORD","TOKEN","SECRET"))]
pattern = re.compile(r"(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|AIza[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)")
issues = []
tracked = subprocess.run(["git","-C",str(ROOT),"ls-files","-z"],capture_output=True,text=True)
if tracked.returncode == 0:
    for name in filter(None,tracked.stdout.split("\0")):
        path = Path(name)
        if ((path.name.startswith(".env") and path.name != ".env.example") or path.name == "secrets.toml"
                or path.suffix in {".pem",".key",".p12",".pfx"}
                or any(part in {".venv",".python",".crewai-storage","output"} for part in path.parts)):
            issues.append("Sensitive/generated file already tracked by Git: "+name)
count = 0
for path in sorted(set(candidate_paths)):
    if not path.exists() or path.suffix in {".png",".jpg",".zip",".pyc"}:
        continue
    if path.name == "secrets.toml" or (path.name.startswith(".env") and path.name != ".env.example"):
        issues.append(f"Sensitive file in upload set: {path.relative_to(ROOT)}")
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError:
        continue
    count += 1
    for number,line in enumerate(text.splitlines(),1):
        if pattern.search(line) or any(secret in line for secret in secrets):
            issues.append(f"Possible secret: {path.relative_to(ROOT)}:{number}")
# Exercise the real gitignore parser without creating/changing this project's .git.
with tempfile.TemporaryDirectory(prefix="amar-tax-ignore-check-") as directory:
    temp = Path(directory).resolve()
    assert temp.parent == Path(tempfile.gettempdir()).resolve()
    subprocess.run(["git","init","-q",str(temp)],check=True,capture_output=True)
    probes = [".env",".env.production",".streamlit/secrets.toml",".venv/test",".python/test","output/report.json","private.key",".crewai-storage/test.db","Amar-Tax-Submission.zip"]
    result = subprocess.run(["git","--git-dir="+str(temp/".git"),"--work-tree="+str(ROOT),"check-ignore","--no-index","-z","--stdin"],input="\0".join(probes)+"\0",text=True,capture_output=True)
    ignored = set(result.stdout.split("\0"))
    for probe in probes:
        if probe not in ignored:
            issues.append("Not ignored: "+probe)
    allowed = subprocess.run(["git","--git-dir="+str(temp/".git"),"--work-tree="+str(ROOT),"check-ignore","--no-index","-z","--stdin"],input=".env.example\0uv.lock\0render.yaml\0",text=True,capture_output=True)
    for path in filter(None, allowed.stdout.split("\0")):
        issues.append("Required file incorrectly ignored: "+path)
print(f"Scanned {count} text files. Actual .env credential values were checked locally and were not printed.")
if issues:
    print("\n".join(issues))
    raise SystemExit(1)
print("PASS: no detected secrets in upload candidates; gitignore checks passed.")
