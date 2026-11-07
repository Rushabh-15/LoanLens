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