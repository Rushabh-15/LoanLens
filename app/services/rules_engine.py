from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

PAISA = Decimal("0.01")


def _require_decimal(name: str, value) -> None:
    """Raise TypeError unless value is a Decimal; floats must never reach money maths."""
    if not isinstance(value, Decimal):
        raise TypeError(f"{name} must be a Decimal.")


@dataclass(frozen=True)
class LendingPolicy:
    """Underwriting limits owned by the risk team. All limits are inclusive."""

    max_foir: Decimal = Decimal("0.50")
    min_monthly_income: Decimal = Decimal("15000")
    max_loan_to_income_multiple: Decimal = Decimal("20")
    default_annual_rate: Decimal = Decimal("12")


DEFAULT_POLICY = LendingPolicy()


def calculate_emi(principal: Decimal, annual_rate: Decimal, tenure_months: int) -> Decimal:
    """
    Calculate the Equated Monthly Installment (EMI) for a loan.

    :param principal: The principal loan amount as a Decimal.
    :param annual_rate: The annual interest rate as a Decimal (percentage).
    :param tenure_months: The loan tenure in months as an integer.
    :return: The EMI as a Decimal, rounded half-up to the paisa.
    """
    _require_decimal("principal", principal)
    _require_decimal("annual_rate", annual_rate)
    if tenure_months <= 0:
        raise ValueError("tenure_months must be a positive integer.")

    monthly_rate = annual_rate / Decimal("12") / Decimal("100")

    if monthly_rate == 0:
        emi = principal / Decimal(tenure_months)
    else:
        growth = (1 + monthly_rate) ** tenure_months
        emi = principal * monthly_rate * growth / (growth - 1)

    return emi.quantize(PAISA, rounding=ROUND_HALF_UP)


def calculate_foir(existing_emis: Decimal, new_emi: Decimal, monthly_income: Decimal) -> Decimal:
    """
    Calculate the Fixed Obligation to Income Ratio (FOIR).

    :param existing_emis: The total of existing EMIs as a Decimal.
    :param new_emi: The new EMI to be added as a Decimal.
    :param monthly_income: The applicant's monthly income as a Decimal.
    :return: FOIR as an unrounded Decimal ratio, so a limit comparison is exact.
    """
    _require_decimal("existing_emis", existing_emis)
    _require_decimal("new_emi", new_emi)
    _require_decimal("monthly_income", monthly_income)
    if monthly_income <= 0:
        raise ValueError("monthly_income must be a positive value.")

    return (existing_emis + new_emi) / monthly_income


def evaluate_risk_flags(
    *,
    foir: Decimal,
    monthly_income: Decimal,
    requested_amount: Decimal,
    policy: LendingPolicy,
) -> list[str]:
    """
    Return decline flags for valid inputs under the given policy.

    Limits are inclusive: a value exactly on a limit passes.
    Inputs must already be validated by analysis.validate_inputs().

    :param foir: The calculated FOIR as a Decimal.
    :param monthly_income: The applicant's monthly income as a Decimal.
    :param requested_amount: The requested loan amount as a Decimal.
    :param policy: The LendingPolicy whose limits apply.
    :return: Flag codes in a fixed order; empty for a clean application.
    """
    _require_decimal("foir", foir)
    _require_decimal("monthly_income", monthly_income)
    _require_decimal("requested_amount", requested_amount)

    flags = []

    if foir > policy.max_foir:
        flags.append("FOIR_TOO_HIGH")

    if monthly_income < policy.min_monthly_income:
        flags.append("INCOME_BELOW_MINIMUM")

    if requested_amount > monthly_income * policy.max_loan_to_income_multiple:
        flags.append("AMOUNT_DISPROPORTIONATE")

    return flags