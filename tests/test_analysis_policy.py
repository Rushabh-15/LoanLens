from decimal import Decimal

from app.models.schemas import DecisionType
from app.services.analysis import analyze_applicant, to_decimal
from app.services.rules_engine import LendingPolicy


ZERO_RATE = LendingPolicy(default_annual_rate=Decimal("0"))


def applicant(**overrides) -> dict:
    """Return applicant data with float amounts, as extraction supplies them."""
    data = {
        "name": "Aarav Mehta",
        "age": 29,
        "employment_type": "salaried",
        "employer": "TCS",
        "monthly_income": 90000.0,
        "existing_emis": 5000.0,
        "requested_amount": 600000.0,
        "tenure_months": 36,
        "purpose": "home renovation",
    }
    data.update(overrides)
    return data


def test_to_decimal_keeps_the_written_value():
    # Decimal(0.1) would be 0.1000000000000000055511151231257827...
    assert to_decimal(0.1) == Decimal("0.1")
    assert to_decimal(15000) == Decimal("15000")


def test_float_inputs_produce_decimal_metrics():
    result = analyze_applicant(applicant())

    assert result.emi == Decimal("19928.59")
    assert isinstance(result.foir, Decimal)
    assert result.decision == DecisionType.ELIGIBLE


def test_default_rate_comes_from_the_policy():
    result = analyze_applicant(applicant(), policy=ZERO_RATE)

    # 6,00,000 / 36 = 16,666.666... rounded half-up to the paisa
    assert result.emi == Decimal("16666.67")


def test_foir_exactly_at_limit_is_eligible_end_to_end():
    # EMI = 6,00,000 / 12 = 50,000; FOIR = (10,000 + 50,000) / 1,20,000 = 0.5
    result = analyze_applicant(
        applicant(monthly_income=120000.0, existing_emis=10000.0, tenure_months=12),
        policy=ZERO_RATE,
    )

    assert result.foir == Decimal("0.5")
    assert result.risk_flags == []
    assert result.decision == DecisionType.ELIGIBLE


def test_stricter_policy_declines_the_same_applicant():
    # FOIR = (5,000 + 19,928.59) / 90,000 = 0.277
    strict = LendingPolicy(max_foir=Decimal("0.25"))

    assert analyze_applicant(applicant()).decision == DecisionType.ELIGIBLE

    result = analyze_applicant(applicant(), policy=strict)
    assert result.risk_flags == ["FOIR_TOO_HIGH"]
    assert result.decision == DecisionType.DECLINE