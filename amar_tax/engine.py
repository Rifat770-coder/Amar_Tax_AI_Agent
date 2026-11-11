"""Deterministic, Decimal-based tools shared by the crew and offline runner."""
from decimal import Decimal, ROUND_HALF_UP

from .models import Calculation, Classification, Documents, Profile, Report, Review, SlabLine

D = Decimal
LABELS = {"general":"General", "female":"Female", "senior_65_plus":"Senior 65+",
          "disabled":"Disabled", "freedom_fighter":"Freedom Fighter"}


def money(value: Decimal) -> Decimal:
    return value.quantize(D("0.01"), rounding=ROUND_HALF_UP)


def classify(profile: Profile, db: dict) -> Classification:
    eligible = ["general"]
    if profile.gender == "female":
        eligible.append("female")
    if profile.age >= 65:
        eligible.append("senior_65_plus")
    if profile.disabled:
        eligible.append("disabled")
    if profile.freedom_fighter:
        eligible.append("freedom_fighter")
    category = max(eligible, key=lambda c: db["thresholds"][c])
    threshold = D(db["thresholds"][category])
    warnings = []
    if profile.age < 18 and profile.wants_independent_filing:
        warnings.append("Minor cannot file independently; guardian assistance is required.")
    if profile.investment > profile.total_income:
        warnings.append("Investment exceeds income, please verify.")
    mandatory = profile.total_income > threshold
    if not mandatory:
        warnings.append("Filing is not mandatory under this simulated income-only rule; no minimum tax applies at or below the threshold.")
    if profile.claims_required_to_file and not mandatory:
        warnings.append("Your required-to-file claim conflicts with the simulated income threshold.")
    return Classification(category=LABELS[category], threshold=threshold,
                          minimum_tax=D(db["minimum_tax"][profile.location]),
                          filing_mandatory=mandatory, can_file_independently=profile.age >= 18,
                          warnings=warnings)


def calculate(profile: Profile, classification: Classification, db: dict) -> Calculation:
    remaining = max(D(0), profile.total_income - classification.threshold)
    lines = []
    for slab in db["slabs_after_threshold"]:
        if remaining <= 0:
            break
        amount = remaining if slab["limit"] is None else min(remaining, D(slab["limit"]))
        rate = D(str(slab["rate"]))
        lines.append(SlabLine(amount=amount, rate=rate, tax=amount * rate))
        remaining -= amount
    gross = money(sum((line.tax for line in lines), D(0)))
    allowable = min(profile.investment, profile.total_income * D(str(db["investment_rebate"]["max_investment_percent_of_income"])))
    rebate = money(allowable * D(str(db["investment_rebate"]["rate"])))
    minimum = classification.minimum_tax if profile.total_income > classification.threshold else D(0)
    net = money(max(gross - rebate, minimum, D(0)))
    return Calculation(total_income=profile.total_income, gross_tax=gross,
                       allowable_investment=allowable, rebate=rebate,
                       minimum_tax_applied=minimum, net_tax=net, slabs=lines)


def organize(profile: Profile, db: dict) -> Documents:
    docs = list(db["required_docs"]["common"])
    warnings = []
    if not profile.has_tin:
        docs.insert(0, "TIN Registration")
        warnings.append("No TIN: complete TIN Registration before filing.")
    profession = profile.profession.casefold()
    aliases = {"software engineer":"salaried", "employee":"salaried", "freelance":"freelancer",
               "businessperson":"business"}
    profession = aliases.get(profession, profession)
    kinds = {s.kind for s in profile.income_sources if s.amount > 0}
    if profession in db["required_docs"] and profession != "common":
        kinds.add(profession)
    else:
        warnings.append("Profession not in DB; using the general checklist plus known income-source documents.")
    if profile.investment > 0:
        kinds.add("investor")
    for kind in sorted(kinds):
        docs.extend(db["required_docs"].get(kind, []))
    return Documents(checklist=list(dict.fromkeys(docs)), warnings=warnings)


def review(profile: Profile, classification: Classification, calculation: Calculation,
           documents: Documents, db: dict) -> Review:
    findings = list(classification.warnings) + list(documents.warnings)
    expected_c = classify(profile, db)
    expected_t = calculate(profile, expected_c, db)
    expected_d = organize(profile, db)
    for label, actual, expected in [("Classifier", classification, expected_c),
                                    ("Calculator", calculation, expected_t),
                                    ("Organizer", documents, expected_d)]:
        if actual != expected:
            findings.append(f"{label} output differs from deterministic source-of-truth validation.")
    return Review(status="Flagged" if findings else "Passed", findings=list(dict.fromkeys(findings)))


def run_offline(profile: Profile, db: dict, source: str) -> Report:
    c = classify(profile, db)
    t = calculate(profile, c, db)
    d = organize(profile, db)
    return Report(profile=profile, classification=c, calculation=t, documents=d,
                  review=review(profile, c, t, d, db), mode="offline (deterministic; no LLM agents)",
                  rules_source=source)
