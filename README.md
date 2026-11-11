![Amar Tax dashboard](docs/Screenshot%202026-11-11%20211056.png)

[**Live app — Amar Tax**](https://amar-tax-ai-agent.onrender.com/)

# Amar Tax — AI Tax Readiness Agent

A CrewAI assignment project that turns a taxpayer profile into a tax readiness report using the supplied **simulated Bangladesh 2026–27 database**. It includes an English Markdown table, a four-line Bangla summary, document checklist, slab calculation and compliance review. It is an educational project, not a real tax-filing service.

## Features

- Modern Streamlit dashboard with separate profile, analytics, report, calculation and documents views.
- Four sequential CrewAI agents with roles, goals, backstories, custom tools and Pydantic outputs.
- Exact Decimal calculations; the assignment database is the only source of tax rules.
- Custom OpenAI-compatible API configured on the server through environment variables.
- Offline mode, API status indicators, bounded AI execution and explicitly labeled fallback reports.
- Markdown/JSON downloads, input validation and all assignment edge cases.
- Public access with optional access-code protection, secret checks, GitHub CI and a Render deployment blueprint.

## Quick start — Windows

Install Python 3.11–3.13 or [uv](https://docs.astral.sh/uv/). Double-click **`start.bat`**, or run:

```powershell
cd P:\Ass_2
.\start.bat
```

First setup needs internet. The launcher installs UI/CrewAI dependencies, starts the app and opens http://127.0.0.1:8501. It restarts existing server processes belonging to this project to load current code. Keep the terminal open; Ctrl+C stops the server. `--check` checks dependencies; `--no-browser` skips opening the browser; `--reuse` keeps an existing server.

## Run manually — any supported platform

Python **3.12** is recommended and selected by `.python-version`.

```bash
uv sync --frozen --extra ui --extra crew --extra dev
uv run --no-sync streamlit run app.py
```

Without uv:

```bash
python -m venv .venv
# Windows: .venv\Scripts\python.exe -m pip install -e ".[ui,crew,dev]"
# Linux/macOS:
.venv/bin/python -m pip install -e '.[ui,crew,dev]'
.venv/bin/python -m streamlit run app.py
```

## API configuration

Copy `.env.example` to `.env` locally, and replace the existing values. Do not commit `.env`.

```dotenv
OPENAI_API_KEY=your-provider-key
OPENAI_BASE_URL=https://your-api-server.example/v1
AMAR_TAX_MODEL=exact-model-id-from-your-provider
AMAR_TAX_CREW_TIMEOUT=60
# Optional: leave unset for public access, including on Render.
# AMAR_TAX_APP_PASSWORD=a-long-random-app-access-code
```

Use the selected provider's own API key. Omit `OPENAI_BASE_URL` to use the standard OpenAI endpoint. The model must support tool calling and structured output. Credentials belong on the server; there are no API key fields in the UI. The app access code is different from the API key. For a public Render deployment, remove `AMAR_TAX_APP_PASSWORD` from the service environment and redeploy the updated code. Setting it enables the optional access-code screen.

The UI reloads `.env` on each rerun; use **API আবার যাচাই করুন** after edits. CLI loads `.env` at startup. Local `.env` entries override matching shell values; removing an entry restores the original shell value. On Render, configure Environment settings instead of uploading `.env`.

**Offline mode needs no provider key.** CrewAI sends the entered profile to the configured provider and may incur provider charges. A green connection light verifies model metadata access; it does not guarantee generation availability or credits.

## Workflow

**Dashboard → Create report → Taxpayer profile → Generate → Dashboard results.**

The sidebar opens separate views. Analytics, report, calculation and documents use the same session report without rerunning agents. Submitted profile values are restored when editing. Downloads are available on Dashboard and Tax report. Reports disappear after a new browser session or server restart; there is no persistent user account database.

## Agent design

| Agent | Role and responsibility | Task context |
| --- | --- | --- |
| Classifier | Senior Taxpayer Classification Officer: category, filing eligibility, threshold and location minimum | Validated profile and DB |
| Calculator | Chartered Tax Accountant: slabs, capped investment rebate, payable tax | Classifier task |
| Organizer | Return Filing Documentation Officer: profession/source/TIN documents | Classifier + Calculator |
| Reviewer | Compliance & Audit Reviewer: cross-check all outputs, Passed/Flagged | All three earlier tasks |

`amar_tax/crew.py` defines every persona and the `@tool` functions. All tasks use `output_pydantic`; explicit `context=[...]` passes earlier outputs; agents and crew use `verbose=True`. A final deterministic check prevents incorrect agent figures from being published as successful AI output.

## Rules and assumptions

1. `amar_tax/data/tax_db.json` is the assignment source of truth. No real NBR rules or additional exemptions are introduced.
2. Total taxable income is the sum of all annual income sources, including freelancing. Do not enter the same income twice.
3. Category thresholds: General 350,000; Female/Senior 65+ 400,000; Disabled 475,000; Freedom Fighter 500,000 BDT. Multiple categories use the highest threshold; the Female/Senior tie uses Female first.
4. Filing is mandatory only when income exceeds the selected threshold under the simulated income-only rule. At or below it, payable tax and applied minimum tax are zero. Real-world filing triggers are outside scope.
5. Slabs apply after the threshold: next 100,000 at 5%, 400,000 at 10%, 500,000 at 15%, 500,000 at 20%, remainder at 25%.
6. Allowable investment = min(actual investment, 20% of income); rebate = 15% of allowable investment. Above the threshold, net tax = max(gross minus rebate, location minimum).
7. Minimum tax: Dhaka/Chattogram city 5,000; other city corporations 4,000; rest of country 3,000 BDT. Location is selected explicitly, not guessed from free text.
8. Decimal arithmetic is used, with ROUND_HALF_UP to two decimal places for monetary totals. Fractional ages, negative/non-finite income, excess precision and unsupported amounts are rejected.
9. Minors cannot file independently. Arithmetic remains available as an estimate, with the guardian warning.
10. Investment above income is flagged; calculation still uses the investment cap. Below-threshold filing claims are checked and explained.
11. Missing TIN adds **TIN Registration** first. Unknown professions use common documents plus documents for recognized income sources. Positive investment adds investor documents. Software engineer/employee map to salaried.
12. Any warning produces Flagged. The assignment's main example produces Passed.
13. Optional remote rules must exactly match the supplied DB; failures, malformed or different rules fall back to the local DB with a log message.
14. UI AI execution defaults to a 60-second total deadline, configurable from 10–180 seconds. Individual model calls use 20-second timeouts with automatic retries disabled. Failed/timed-out runs produce clearly labeled, Flagged offline reports.
15. Worker reports travel through a separate temporary result file; verbose logs cannot corrupt that channel. Credentials travel through stdin, not files. Worker report/storage files are removed after completion.

## CLI

```bash
uv run --no-sync python -m amar_tax examples/01_example.json
uv run --no-sync python -m amar_tax examples/01_example.json --mode crew --strict-crew
uv run --no-sync python -m amar_tax examples/01_example.json --rules-url http://127.0.0.1:1/rules
```

CLI writes `output/report.md` and JSON. Exit codes: 0 for a generated report (including valid Flagged cases); 2 for invalid input; 3 for strict CrewAI failure. Existing output files are not deleted on failure. Without `--strict-crew`, CLI also supports explicit offline fallback.

## Tests and evidence

```bash
uv run --no-sync pytest -q
uv run --no-sync python scripts/security_check.py
uv run --no-sync python scripts/run_examples.py
```

Four scenario screenshots and synthetic example reports are in `evidence/`. The main example gives gross **140,000**, rebate **30,000**, net **110,000 BDT**. A synthetic male example gives net **120,000 BDT**. Previous authenticated live custom API runs completed with Passed; model/provider availability can change. Automated tests mock provider calls and do not require real credentials.

## GitHub, Render and video

- [Security review and known dependency findings](SECURITY.md)
- [GitHub upload and Render deployment guide](docs/DEPLOY_RENDER.md)
- [Four-minute Google Flow storyboard: 24 connected ten-second prompts](docs/VIDEO_FLOW_PROMPTS.md)
- [Real demo recording checklist](docs/DEMO.md)

`render.yaml` prepares a Python web service with secret environment settings, access-code protection and `/_stcore/health`. It does not deploy anything until you connect the repository in Render. The included free plan is a starting point for demonstration; CrewAI is memory-heavy and may need more resources. Render Linux execution and memory capacity have not been verified from this Windows environment.

## Source map

`app.py` is the Streamlit entry point. `amar_tax/web_app.py` handles UI/navigation; `dashboard.py` and `data/dashboard.css` provide presentation. `models.py`, `engine.py` and `report.py` validate, calculate and render. `crew.py`, `runner.py`, `crew_worker.py` and `service.py` handle agents and fallback. `settings.py`, `connection.py`, `api_status.py`, `network.py` and `access.py` manage configuration, checks and access.
