# Verification performed

- Python 3.12.13; CrewAI 1.15.39; Pydantic 2.12.5.
- Latest complete suite: **68 passed**, covering standard/custom server settings, public access-code protection, redirect safety, worker success/timeout behavior, noisy stdout isolation, strict report validation and temporary-result cleanup. Automated API responses are mocked.
- After separating worker results from verbose logs, a live synthetic male profile with all six UI income-source fields completed in **30.3 seconds**, producing **120,000 BDT**, **Passed**, and **CrewAI** mode. See `live_male_report.md` and its JSON counterpart.
- Live custom API verification: the `ashboran` model route passed a synthetic tool-call probe and the complete four-agent workflow. The UI's bounded pipeline then completed in **32.4 seconds**, producing **110,000 BDT** net tax and **Passed**, with mode **CrewAI (four sequential LLM agents)**. This run did not use offline fallback. See `provider_check_report.md` and `live_crew_report.json`.
- `python scripts/run_examples.py`: four valid scenarios exited 0; negative-income scenario exited 2.
- Main example: gross 140,000 BDT, rebate 30,000 BDT, net payable 110,000 BDT; Passed.
- Minor: Flagged, independent filing disallowed, TIN Registration first.
- Below threshold: Flagged explanation and conflicting filing claim; zero payable and zero applied minimum.
- Excess investment: Flagged; allowable investment 160,000 BDT and net payable 16,000 BDT.
- HTML screenshots display the actual offline JSON report results, labeled as offline.
- Automated Crew integration tests constructed real Agent/Crew/Task/tool objects while stubbing kickoff. Separate live checks used the public assignment profile and synthetic prompts only.
- Custom API generation was verified successfully and the active server model was updated to the tested route. Credential values are never included in evidence or the source archive. The assignment video remains a submission step.

- Dashboard workflow verified: default landing, create-report navigation, automatic return after generation, active sidebar views, unchanged report while navigating, restored submitted profile, and first-report guidance.

- GitHub/Render preparation: secret scan and gitignore parser checks passed; source ZIP checked against actual local `.env` secrets; Render Blueprint validated against the official schema. No GitHub push or Render deployment was performed.
- Dependency audit reported 5 records / 4 unique advisories in chromadb 1.5.9, without fixed versions. These remain documented in SECURITY.md; a clean vulnerability audit is not claimed.
