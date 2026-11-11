from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class IncomeSource(StrictModel):
    kind: Literal["salaried", "business", "freelancer", "landlord", "investor", "other"]
    amount: Decimal = Field(ge=0, max_digits=15, decimal_places=2)


class Profile(StrictModel):
    age: int = Field(ge=0, le=120, strict=True)
    gender: Literal["male", "female", "other"]
    profession: str = Field(min_length=1, max_length=100)
    income_sources: list[IncomeSource] = Field(min_length=1, max_length=30)
    investment: Decimal = Field(default=Decimal(0), ge=0, max_digits=15, decimal_places=2)
    location: Literal["dhaka_chattogram_city", "other_city_corporation", "rest_of_country"]
    has_tin: bool = Field(strict=True)
    disabled: bool = Field(default=False, strict=True)
    freedom_fighter: bool = Field(default=False, strict=True)
    wants_independent_filing: bool = Field(default=True, strict=True)
    claims_required_to_file: bool = Field(default=False, strict=True)

    @field_validator("profession")
    @classmethod
    def clean_profession(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Profession cannot be blank")
        return value.strip()

    @model_validator(mode="after")
    def bounded_total(self):
        if self.total_income > Decimal("9999999999999.99"):
            raise ValueError("Total income is outside the supported range")
        return self

    @property
    def total_income(self) -> Decimal:
        return sum((s.amount for s in self.income_sources), Decimal(0))


class Classification(StrictModel):
    category: str
    threshold: Decimal
    minimum_tax: Decimal
    filing_mandatory: bool
    can_file_independently: bool
    warnings: list[str]


class SlabLine(StrictModel):
    amount: Decimal
    rate: Decimal
    tax: Decimal


class Calculation(StrictModel):
    total_income: Decimal
    gross_tax: Decimal
    allowable_investment: Decimal
    rebate: Decimal
    minimum_tax_applied: Decimal
    net_tax: Decimal
    slabs: list[SlabLine]


class Documents(StrictModel):
    checklist: list[str]
    warnings: list[str]


class Review(StrictModel):
    status: Literal["Passed", "Flagged"]
    findings: list[str]


class Report(StrictModel):
    profile: Profile
    classification: Classification
    calculation: Calculation
    documents: Documents
    review: Review
    mode: str
    rules_source: str
