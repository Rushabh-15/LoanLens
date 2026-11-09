import dataclasses
from decimal import Decimal

import pytest

from app.services.rules_engine import (
    DEFAULT_POLICY,
    LendingPolicy,
    calculate_emi,
    calculate_foir,
    evaluate_risk_flags,
)


@pytest.mark.parametrize(
    "principal, annual_rate, tenure_months, expected",
    [
        pytest.param("600000", "12", 36, "19928.59", id="known_value_36_months"),
        pytest.param("600000", "12", 1, "606000.00", id="one_month"),
        pytest.param("120000", "0", 12, "10000.00", id="zero_rate_even"),
        pytest.param("100000", "0", 3, "33333.33", id="zero_rate_uneven"),
        pytest.param("500000", "12", 60, "11122.22", id="old_value_60_months"),
        pytest.param("200000", "12", 24, "9414.69", id="old_value_24_months"),
    ],
)
def test_emi_known_values(principal, annual_rate, tenure_months, expected):
    result = calculate_emi(Decimal(principal), Decimal(annual_rate), tenure_months)

    assert result == Decimal(expected)


@pytest.mark.parametrize("annual_rate", ["12", "0"], ids=["with_interest", "zero_rate"])
def test_emi_is_a_decimal_rounded_to_paisa(annual_rate):
    result = calculate_emi(Decimal("120000"), Decimal(annual_rate), 12)

    assert isinstance(result, Decimal)
    assert result.as_tuple().exponent == -2


@pytest.mark.parametrize("tenure_months", [0, -1])
def test_emi_rejects_non_positive_tenure(tenure_months):
    with pytest.raises(ValueError):
        calculate_emi(Decimal("600000"), Decimal("12"), tenure_months)


@pytest.mark.parametrize("annual_rate", ["12", "0"], ids=["with_interest", "zero_rate"])
def test_emi_rejects_float_principal(annual_rate):
    with pytest.raises(TypeError):
        calculate_emi(600000.0, Decimal(annual_rate), 36)

def test_emi_rounds_half_up_at_exact_half_paisa():
    # 1,00,000.05 / 2 = 50,000.025: half-up gives .03, half-even gives .02
    result = calculate_emi(Decimal("100000.05"), Decimal("0"), 2)

    assert result == Decimal("50000.03")

def test_foir_known_value_is_not_rounded():
    result = calculate_foir(Decimal("15000"), Decimal("11122.22"), Decimal("60000"))

    assert result == Decimal("0.4353703333333333333333333333")


def test_foir_can_land_exactly_on_half():
    result = calculate_foir(Decimal("15000"), Decimal("10000.00"), Decimal("50000"))

    assert result == Decimal("0.50")


def test_foir_with_no_existing_emis():
    result = calculate_foir(Decimal("0"), Decimal("19928.59"), Decimal("90000"))

    assert result == Decimal("0.2214287777777777777777777778")


@pytest.mark.parametrize("monthly_income", ["0", "-1"])
def test_foir_rejects_non_positive_income(monthly_income):
    with pytest.raises(ValueError):
        calculate_foir(Decimal("15000"), Decimal("11122.22"), Decimal(monthly_income))


@pytest.mark.parametrize("argument", ["existing_emis", "new_emi", "monthly_income"])
def test_foir_rejects_float_arguments(argument):
    arguments = {
        "existing_emis": Decimal("15000"),
        "new_emi": Decimal("11122.22"),
        "monthly_income": Decimal("60000"),
    }
    arguments[argument] = float(arguments[argument])

    with pytest.raises(TypeError):
        calculate_foir(**arguments)



def flags_for(foir="0.30", monthly_income="60000", requested_amount="600000",
              policy=DEFAULT_POLICY):
    return evaluate_risk_flags(
        foir=Decimal(foir),
        monthly_income=Decimal(monthly_income),
        requested_amount=Decimal(requested_amount),
        policy=policy,
    )


def test_default_policy_values():
    assert DEFAULT_POLICY.max_foir == Decimal("0.50")
    assert DEFAULT_POLICY.min_monthly_income == Decimal("15000")
    assert DEFAULT_POLICY.max_loan_to_income_multiple == Decimal("20")
    assert DEFAULT_POLICY.default_annual_rate == Decimal("12")


def test_policy_cannot_be_changed_after_creation():
    with pytest.raises(dataclasses.FrozenInstanceError):
        DEFAULT_POLICY.max_foir = Decimal("0.60")


def test_clean_application_has_no_flags():
    assert flags_for() == []


@pytest.mark.parametrize(
    "overrides, expected",
    [
        pytest.param({"foir": "0.50"}, [], id="foir_at_limit"),
        pytest.param({"foir": "0.5001"}, ["FOIR_TOO_HIGH"], id="foir_over_limit"),
        pytest.param({"monthly_income": "15000", "requested_amount": "100000"}, [],
                     id="income_at_minimum"),
        pytest.param({"monthly_income": "14999.99", "requested_amount": "100000"},
                     ["INCOME_BELOW_MINIMUM"], id="income_below_minimum"),
        pytest.param({"requested_amount": "1200000"}, [], id="amount_at_20x"),
        pytest.param({"requested_amount": "1200000.01"}, ["AMOUNT_DISPROPORTIONATE"],
                     id="amount_over_20x"),
    ],
)
def test_thresholds_at_exact_boundaries(overrides, expected):
    assert flags_for(**overrides) == expected


def test_all_three_flags_in_order():
    assert flags_for(foir="0.60", monthly_income="10000", requested_amount="500000") == [
        "FOIR_TOO_HIGH",
        "INCOME_BELOW_MINIMUM",
        "AMOUNT_DISPROPORTIONATE",
    ]


def test_custom_policy_changes_the_outcome():
    strict = LendingPolicy(max_foir=Decimal("0.40"))

    assert flags_for(foir="0.45") == []
    assert flags_for(foir="0.45", policy=strict) == ["FOIR_TOO_HIGH"]


@pytest.mark.parametrize("argument", ["foir", "monthly_income", "requested_amount"])
def test_risk_flags_reject_float_arguments(argument):
    arguments = {
        "foir": Decimal("0.30"),
        "monthly_income": Decimal("60000"),
        "requested_amount": Decimal("600000"),
    }
    arguments[argument] = float(arguments[argument])

    with pytest.raises(TypeError):
        evaluate_risk_flags(**arguments, policy=DEFAULT_POLICY)