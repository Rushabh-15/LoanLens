from decimal import Decimal

import pytest

from app.models.schemas import DecisionType, ExtractionStatus
from app.services import analysis
from app.services.analysis import FIELD_RULES, analyze_applicant, validate_inputs
from app.services.decision import CRITICAL_FIELDS


def applicant(**overrides) -> dict:
    data = {
        "name": "Aarav Mehta",
        "age": 29,
        "employment_type": "salaried",
        "employer": "TCS",
        "monthly_income": 90000,
        "existing_emis": 5000,
        "requested_amount": 600000,
        "tenure_months": 36,
        "purpose": "home renovation",
    }
    data.update(overrides)
    return data


# FOIR = (5,000 + 19,928.59) / 30,000 = 0.83, so the rules would decline.
# 6,00,000 is exactly 20 x 30,000, which the inclusive limit allows.
HIGH_FOIR = {"monthly_income": 30000}


@pytest.fixture
def forbid_financial_calculations(monkeypatch):
    def unexpected_calculation(*args, **kwargs):
        pytest.fail("This path must not calculate EMI or FOIR.")

    monkeypatch.setattr(analysis, "calculate_emi", unexpected_calculation)
    monkeypatch.setattr(analysis, "calculate_foir", unexpected_calculation)


# -----------------------------
# validate_inputs()
# -----------------------------
def test_every_critical_field_has_a_validation_rule():
    assert set(FIELD_RULES) == set(CRITICAL_FIELDS)


def test_validate_inputs_returns_field_names_in_critical_order():
    data = applicant(tenure_months=None, monthly_income=0, age=16)

    missing_fields, invalid_fields = validate_inputs(data)

    assert missing_fields == ["tenure_months"]
    assert invalid_fields == ["age", "monthly_income"]


def test_validate_inputs_accepts_a_valid_applicant():
    assert validate_inputs(applicant()) == ([], [])


# -----------------------------
# Row 1: extraction failed
# -----------------------------
def test_failed_extraction_skips_validation_and_calculation(
    forbid_financial_calculations,
):
    # all_low() gives None everywhere; none of it should be reported.
    empty = {field_name: None for field_name in applicant()}

    result = analyze_applicant(
        empty,
        extraction_status=ExtractionStatus.TIMEOUT,
        low_confidence_fields=CRITICAL_FIELDS,
    )

    assert result.decision == DecisionType.NEEDS_REVIEW
    assert result.reason_codes == ["EXTRACTION_FAILED:timeout"]
    assert result.risk_flags == []
    assert result.emi == Decimal("0")
    assert result.foir == Decimal("0")


# -----------------------------
# Row 3: low confidence on valid values
# -----------------------------
def test_low_confidence_still_calculates_metrics():
    result = analyze_applicant(
        applicant(),
        low_confidence_fields=("monthly_income",),
    )

    assert result.decision == DecisionType.NEEDS_REVIEW
    assert result.reason_codes == ["LOW_CONFIDENCE:monthly_income"]
    assert result.emi == Decimal("19928.59")
    assert result.foir > 0
    assert result.risk_flags == []


def test_low_confidence_outranks_decline_but_the_flag_stays_visible():
    result = analyze_applicant(
        applicant(**HIGH_FOIR),
        low_confidence_fields=("monthly_income",),
    )

    assert result.decision == DecisionType.NEEDS_REVIEW
    assert result.reason_codes == ["LOW_CONFIDENCE:monthly_income"]
    assert result.risk_flags == ["FOIR_TOO_HIGH"]


# -----------------------------
# Rows 4 and 5
# -----------------------------
def test_decline_without_review_causes():
    result = analyze_applicant(applicant(**HIGH_FOIR))

    assert result.decision == DecisionType.DECLINE
    assert result.reason_codes == ["FOIR_TOO_HIGH"]
    assert result.risk_flags == ["FOIR_TOO_HIGH"]


def test_clean_applicant_is_eligible_with_no_codes():
    result = analyze_applicant(applicant())

    assert result.decision == DecisionType.ELIGIBLE
    assert result.reason_codes == []
    assert result.reason == "Passed all checks."