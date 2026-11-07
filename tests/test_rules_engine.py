from decimal import Decimal

import pytest

from app.services.rules_engine import calculate_emi


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