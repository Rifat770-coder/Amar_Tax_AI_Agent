import json
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from amar_tax.database import load_database
from amar_tax.engine import classify, calculate, organize, review, run_offline
from amar_tax.models import Profile
from amar_tax.report import render_markdown

ROOT = Path(__file__).resolve().parents[1]


def profile(name="01_example"):
    return Profile.model_validate_json((ROOT / "examples" / f"{name}.json").read_text())


def changed(**changes):
    data = profile().model_dump()
    data.update(changes)
    return Profile.model_validate(data)


@pytest.fixture
def db():
    return load_database()[0]


def test_assignment_example(db):
    r = run_offline(profile(), db, "local")
    assert r.classification.category == "Female"
    assert r.calculation.gross_tax == D(140000)
    assert r.calculation.rebate == D(30000)
    assert r.calculation.net_tax == D(110000)
    assert r.review.status == "Passed"
    assert "Foreign Remittance Proof" in r.documents.checklist
    assert "Investment Certificates (DPS/Sanchaypatra)" in r.documents.checklist


def test_minor_and_missing_tin(db):
    r = run_offline(profile("02_minor"), db, "local")
    assert r.review.status == "Flagged"
    assert not r.classification.can_file_independently
    assert any("Minor cannot file independently" in w for w in r.review.findings)
    assert r.documents.checklist[0] == "TIN Registration"


def test_below_threshold_claim_and_minimum(db):
    r = run_offline(profile("03_below_threshold"), db, "local")
    assert r.calculation.net_tax == 0
    assert r.calculation.minimum_tax_applied == 0
    assert not r.classification.filing_mandatory
    assert any("claim conflicts" in w for w in r.review.findings)


def test_excess_investment_cap(db):
    r = run_offline(profile("04_excess_investment"), db, "local")
    assert r.calculation.allowable_investment == D(160000)
    assert r.calculation.rebate == D(24000)
    assert r.calculation.net_tax == D(16000)
    assert any("Investment exceeds" in w for w in r.review.findings)


@pytest.mark.parametrize("amount", [-50000, "NaN", "Infinity", "1000000000000000000000", "1.001"])
def test_invalid_income(amount):
    with pytest.raises(ValidationError):
        changed(income_sources=[{"kind":"salaried", "amount":amount}])


@pytest.mark.parametrize("age", [-1, 121, 18.5, True])
def test_invalid_age(age):
    with pytest.raises(ValidationError):
        changed(age=age)


def test_unknown_profession_general_fallback(db):
    p = changed(profession="astronaut", income_sources=[{"kind":"other", "amount":500000}], investment=0)
    docs = organize(p, db)
    assert docs.checklist == db["required_docs"]["common"]
    assert any("Profession not in DB" in w for w in docs.warnings)


@pytest.mark.parametrize("income,gross", [(350000,0),(450000,5000),(850000,45000),
                                          (1350000,120000),(1850000,220000),(1950000,245000)])
def test_slab_boundaries(db, income, gross):
    p = changed(gender="male", investment=0, income_sources=[{"kind":"salaried","amount":income}])
    assert calculate(p, classify(p, db), db).gross_tax == D(gross)


@pytest.mark.parametrize("location,minimum", [("dhaka_chattogram_city",5000),
                          ("other_city_corporation",4000),("rest_of_country",3000)])
def test_minimum_above_threshold(db, location, minimum):
    p = changed(location=location, investment=0, income_sources=[{"kind":"salaried","amount":400001}])
    assert calculate(p, classify(p, db), db).net_tax == minimum


def test_category_priority(db):
    assert classify(changed(age=65, gender="male"), db).category == "Senior 65+"
    assert classify(changed(disabled=True), db).threshold == 475000
    assert classify(changed(disabled=True, freedom_fighter=True), db).category == "Freedom Fighter"


def test_reviewer_detects_corruption(db):
    r = run_offline(profile(), db, "local")
    r.calculation.net_tax += 1
    result = review(r.profile, r.classification, r.calculation, r.documents, db)
    assert result.status == "Flagged"
    assert any("Calculator output differs" in w for w in result.findings)


def test_remote_failure_falls_back(db, caplog):
    with patch("amar_tax.database.urlopen", side_effect=OSError("offline")):
        actual, source = load_database("https://example.invalid/rules")
    assert actual == db
    assert "Local DB" in source
    assert "falling back to Local DB" in caplog.text


def test_remote_mismatch_cannot_override(db):
    fake = deepcopy(db)
    fake["thresholds"]["general"] = 0
    with patch("amar_tax.database.urlopen") as request:
        request.return_value.__enter__.return_value.read.return_value = json.dumps(fake).encode()
        actual, source = load_database("https://example.invalid/rules")
    assert actual == db
    assert "Local DB" in source


def test_report_format(db):
    r = run_offline(profile(), db, "local")
    text = render_markdown(r, db)
    assert "| Field | Result |" in text
    assert "110,000.00 BDT" in text
    assert "✅ Passed" in text
    bangla = text.split("## বাংলা সারসংক্ষেপ\n\n")[1].strip().splitlines()
    assert len(bangla) == 4
