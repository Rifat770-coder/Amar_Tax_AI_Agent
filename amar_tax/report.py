from decimal import Decimal

from .models import Report


def bdt(value: Decimal) -> str:
    return f"{value:,.2f} BDT"


def escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_markdown(report: Report, db: dict) -> str:
    c, t, d, r = report.classification, report.calculation, report.documents, report.review
    status = ("✅ " if r.status == "Passed" else "⚠️ ") + r.status
    rows = [
        ("Tax Year", db["tax_year"]), ("Filing Deadline", db["filing_deadline"]),
        ("Taxpayer Category", c.category), ("Total Income", bdt(t.total_income)),
        ("Tax-free Threshold", bdt(c.threshold)),
        ("Filing Mandatory (simulated rule)", "Yes" if c.filing_mandatory else "No"),
        ("Can File Independently", "Yes" if c.can_file_independently else "No"),
        ("Gross Tax (Slab-based)", bdt(t.gross_tax)),
        ("Allowable Investment", bdt(t.allowable_investment)),
        ("Investment Rebate (15%)", bdt(t.rebate)),
        ("Minimum Tax (location)", bdt(c.minimum_tax)),
        ("Minimum Tax Applied", bdt(t.minimum_tax_applied)),
        ("Net Payable Tax", bdt(t.net_tax)),
        ("Documents Needed", "; ".join(d.checklist)),
        ("Compliance Status", status), ("Execution Mode", report.mode),
        ("Rules Source", report.rules_source)]
    lines = ["# Amar Tax — Tax Readiness Report", "",
             "> Simulated assignment rules only. This report is not real tax advice.", "",
             "| Field | Result |", "| :--- | :--- |"]
    lines += [f"| {escape(key)} | {escape(value)} |" for key,value in rows]
    lines += ["", "## Slab calculation", "", "| Income portion | Rate | Tax |", "| :--- | ---: | ---: |"]
    lines += [f"| {bdt(s.amount)} | {s.rate * 100:g}% | {bdt(s.tax)} |" for s in t.slabs]
    if not t.slabs:
        lines.append("| No income above threshold | 0% | 0.00 BDT |")
    lines += ["", "## Review findings", ""]
    lines += ["- " + f for f in r.findings] if r.findings else ["- All source-of-truth checks passed."]
    filing = "রিটার্ন দাখিল বাধ্যতামূলক" if c.filing_mandatory else "রিটার্ন দাখিল বাধ্যতামূলক নয়"
    lines += ["", "## বাংলা সারসংক্ষেপ", "",
              f"এই অ্যাসাইনমেন্টের সরলীকৃত নিয়ম অনুযায়ী {filing}।  ",
              f"মোট আয় {bdt(t.total_income)}; হিসাব অনুযায়ী প্রদেয় কর {bdt(t.net_tax)}।  ",
              "তালিকার কাগজপত্র প্রস্তুত করুন এবং টিআইএন না থাকলে নিবন্ধন করুন।  ",
              ("যাচাইয়ে সতর্কতা পাওয়া গেছে; রিপোর্টের সতর্কবার্তাগুলো দেখুন।" if r.status == "Flagged" else
               "যাচাই সম্পন্ন হয়েছে; এটি শুধু অনুশীলনের জন্য, প্রকৃত কর পরামর্শ নয়।"), ""]
    return "\n".join(lines)
