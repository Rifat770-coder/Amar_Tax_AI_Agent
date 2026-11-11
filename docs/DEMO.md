# Submission demo and capture guide

Target length: 3–5 minutes. Use synthetic profiles in `examples/`. Keep API keys out of the recording.

For Google Flow, use [the connected 24-scene, 4-minute prompt package](VIDEO_FLOW_PROMPTS.md). Capture genuine app/terminal footage first; Flow supplies presentation and continuity, not invented execution evidence.

## Recording script

1. **0:00–0:40 — Purpose and rules.** Explain that Amar Tax follows the supplied simulated DB. Show `tax_db.json`, the profile fields, and the category/slab/rebate rules.
2. **0:40–1:20 — Agent design.** Open `crew.py`. Show all four personas, the `@tool` definitions, `output_pydantic`, explicit context lists, and `verbose=True`.
3. **1:20–2:20 — Live crew example.** Set the API key privately. Run the example using `--mode crew --strict-crew`. Show agent/tool interaction in the terminal and the generated report. Explain 5,000 + 40,000 + 75,000 + 20,000 = 140,000 gross, less 30,000 rebate = 110,000 payable. If the provider fails, fix the credentials before presenting this as a live-agent demonstration.
4. **2:20–3:20 — Error cases.** Run minor, below-threshold, and excess-investment examples. Show Flagged status, TIN Registration first, zero payable below the threshold, and the 20% investment cap. Run invalid income and show exit code 2.
5. **3:20–4:10 — Local fallback and review.** Run an example with `--rules-url http://127.0.0.1:1/rules`; show the Local DB fallback log and unchanged calculation. Explain that the reviewer recomputes figures and compares checklists.
6. **4:10–4:40 — Tests and assumptions.** Run pytest. Show the four-line Bangla summary and README assumptions.

## Required screenshots

Four screenshots of actual executed offline results are included in `evidence/screenshots/`. Their source data is in the adjacent JSON and Markdown. Duplicate generated HTML and old logs were removed during repository cleanup.

To refresh them, generate all examples with `python scripts/run_examples.py`, then run `python scripts/render_evidence.py`. Open `evidence/*.html` in a browser and capture the report with Windows Snipping Tool. Include the net tax, compliance status, and relevant warning. Save actual captures in `evidence/screenshots/`.

Also capture a terminal frame from a successful **real CrewAI run** showing the agent roles and tool calls. Offline logs must be labeled offline. Do not use generated mockups as proof of execution.

Suggested filenames: `01-example.png`, `02-minor.png`, `03-below-threshold.png`, `04-excess-investment.png`, `05-crew-interaction.png`. The final video is a separate submission artifact; this repository provides the recording script, not a prerecorded claim of live execution.
