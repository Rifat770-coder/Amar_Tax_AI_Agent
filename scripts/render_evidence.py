"""Render executed JSON results as readable, explicitly offline HTML evidence."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
escape = html.escape
for path in sorted((ROOT / "evidence").glob("*.json")):
    r = json.loads(path.read_text(encoding="utf-8"))
    c, t = r["classification"], r["calculation"]
    amount = lambda value: f"{float(value):,.2f} BDT"
    rows = [("Taxpayer category", c["category"]), ("Total income", amount(t["total_income"])),
            ("Tax-free threshold", amount(c["threshold"])),
            ("Filing mandatory", "Yes" if c["filing_mandatory"] else "No"),
            ("Independent filing allowed", "Yes" if c["can_file_independently"] else "No"),
            ("Gross tax", amount(t["gross_tax"])), ("Investment rebate", amount(t["rebate"])),
            ("Minimum tax applied", amount(t["minimum_tax_applied"])),
            ("NET PAYABLE TAX", amount(t["net_tax"]))]
    table = "".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k,v in rows)
    docs = "".join(f"<li>{escape(v)}</li>" for v in r["documents"]["checklist"])
    findings = "".join(f"<li>{escape(v)}</li>" for v in r["review"]["findings"])
    if not findings:
        findings = "<li>All source-of-truth checks passed.</li>"
    md = path.with_suffix(".md").read_text(encoding="utf-8")
    bangla = md.split("## বাংলা সারসংক্ষেপ\n\n")[1].strip().replace("  \n", "<br>")
    document = f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Amar Tax evidence</title>
<style>body{{font:17px 'Segoe UI',sans-serif;background:#edf3f6;color:#142c3e;margin:0;padding:35px}}
main{{background:white;max-width:1100px;margin:auto;padding:30px;border-radius:16px}}
h1{{margin:0;color:#076b68}}.badge{{background:#e5f4ef;padding:12px;border-radius:8px}}
.columns{{display:grid;grid-template-columns:1fr 1fr;gap:30px}}table{{border-collapse:collapse;width:100%}}
th,td{{padding:10px;border-bottom:1px solid #dce5ea;text-align:left}}tr:last-child{{background:#e5f4ef;font-weight:bold}}
li{{margin-bottom:9px}}small{{color:#526473}}h2{{font-size:21px}}.bangla{{line-height:1.8}}
</style><main><h1>Amar Tax · Tax Readiness Report</h1><p>{escape(path.stem)}</p>
<p class="badge"><strong>Compliance: {escape(r['review']['status'])}</strong> · {escape(r['mode'])}</p>
<small>Simulated assignment rules only · Tax year 2026–27 · Deadline 2026-11-30<br>
Actual executed offline results; no LLM agent interaction claimed.</small>
<div class="columns"><section><h2>Calculation</h2><table>{table}</table></section>
<section><h2>Documents needed</h2><ol>{docs}</ol></section></div>
<h2>Review findings</h2><ul>{findings}</ul><h2>বাংলা সারসংক্ষেপ</h2><p class="bangla">{bangla}</p>
</main></html>'''
    path.with_suffix(".html").write_text(document, encoding="utf-8")
    print(path.with_suffix(".html").name)
