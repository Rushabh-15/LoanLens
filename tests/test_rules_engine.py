import pytest

from app.services.rules_engine import (
    calculate_emi,
    calculate_foir,
    evaluate_risk_flags
)


def test_emi_basic():
    result = calculate_emi(
        principal=500000,
        annual_rate=12,
        tenure_months=60
    )

    assert result == pytest.approx(11122.22, abs=0.01)


def test_emi_zero_interest():
    result = calculate_emi(
        principal=120000,
        annual_rate=0,
        tenure_months=12
    )

    assert result == pytest.approx(10000.00, abs=0.01)


def test_emi_another_term():
    result = calculate_emi(
        principal=200000,
        annual_rate=12,
        tenure_months=24
    )

    assert result == pytest.approx(9414.69, abs=0.01)


def test_foir_basic():
    result = calculate_foir(
        existing_emis=15000,
        new_emi=11122.22,
        monthly_income=60000
    )

    assert result == pytest.approx(0.4354, abs=0.0001)


def test_foir_zero_income():
    with pytest.raises(ValueError):
        calculate_foir(
            existing_emis=15000,
            new_emi=11122.22,
            monthly_income=0
        )


def test_flag_high_foir():
    flags = evaluate_risk_flags(
        monthly_income=60000,
        existing_emis=25000,
        requested_loan_amount=500000,
        annual_interest_rate=12,
        tenure_months=60
    )

    assert "FOIR_TOO_HIGH" in flags


def test_flag_clean_application():
    flags = evaluate_risk_flags(
        monthly_income=120000,
        existing_emis=5000,
        requested_loan_amount=200000,
        annual_interest_rate=10,
        tenure_months=60
    )

    assert flags == []


def test_flag_income_below_minimum():
    flags = evaluate_risk_flags(
        monthly_income=10000,
        existing_emis=2000,
        requested_loan_amount=100000,
        annual_interest_rate=10,
        tenure_months=24
    )

    assert "INCOME_BELOW_MINIMUM" in flags


def test_flag_amount_disproportionate():
    flags = evaluate_risk_flags(
        monthly_income=20000,
        existing_emis=1000,
        requested_loan_amount=1000000,
        annual_interest_rate=10,
        tenure_months=60
    )

    assert "AMOUNT_DISPROPORTIONATE" in flags


def test_flag_missing_critical_field():
    flags = evaluate_risk_flags(
        monthly_income=None,
        existing_emis=1000,
        requested_loan_amount=200000,
        annual_interest_rate=10,
        tenure_months=60
    )

    assert "MISSING_CRITICAL_FIELD" in flags


def test_flag_zero_income():
    flags = evaluate_risk_flags(
        monthly_income=0,
        existing_emis=1000,
        requested_loan_amount=200000,
        annual_interest_rate=10,
        tenure_months=60
    )

    assert "MISSING_CRITICAL_FIELD" in flags


def test_flag_zero_tenure():
    flags = evaluate_risk_flags(
        monthly_income=50000,
        existing_emis=1000,
        requested_loan_amount=200000,
        annual_interest_rate=10,
        tenure_months=0
    )

    assert "MISSING_CRITICAL_FIELD" in flags