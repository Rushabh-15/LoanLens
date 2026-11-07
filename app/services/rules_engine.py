from decimal import ROUND_HALF_UP, Decimal

PAISA = Decimal("0.01")

def calculate_emi(principal: Decimal, annual_rate: Decimal, tenure_months: int) -> Decimal:
    """
    Calculate the Equated Monthly Installment (EMI) for a loan.

    :param principal: The principal loan amount as a Decimal.
    :param annual_rate: The annual interest rate as a Decimal (percentage).
    :param tenure_months: The loan tenure in months as an integer.
    :return: The EMI amount as a Decimal Rounded half-up to the paisa.
    """
    if not isinstance(principal, Decimal):
        raise TypeError("Principal must be a Decimal.")
    if not isinstance(annual_rate, Decimal):
        raise TypeError("Annual rate must be a Decimal.")
    if tenure_months <= 0:
        raise ValueError("Tenure months must be a positive integer.")

    monthly_rate = annual_rate / Decimal("12") / Decimal("100")
    growth = (1 + monthly_rate) ** tenure_months
    
    if monthly_rate == 0:
        emi = principal / Decimal(tenure_months)
    else:
        emi = principal * monthly_rate * growth / (growth - 1)

    return emi.quantize(PAISA, rounding=ROUND_HALF_UP)


def calculate_foir(existing_emis: Decimal, new_emi: Decimal, monthly_income: Decimal) -> Decimal:
    """
    Calculate the Fixed Obligation to Income Ratio (FOIR).

    :param existing_emis: The total of existing EMIs as a Decimal.
    :param new_emi: The new EMI to be added as a Decimal.
    :param monthly_income: The applicant's monthly income as a Decimal.
    :return: The FOIR as a Decimal (ratio).
    """
    if not isinstance(existing_emis, Decimal):
        raise TypeError("Existing EMIs must be a Decimal.")
    if not isinstance(new_emi, Decimal):
        raise TypeError("New EMI must be a Decimal.")
    if not isinstance(monthly_income, Decimal):
        raise TypeError("Monthly income must be a Decimal.")
    if monthly_income <= 0:
        raise ValueError("Monthly income must be a positive value.")

    total_obligations = existing_emis + new_emi
    foir = total_obligations / monthly_income

    return foir

def _require_decimal(name: str, value) -> None:
    if not isinstance(value, Decimal):
      raise TypeError(f"{name} must be a Decimal.")