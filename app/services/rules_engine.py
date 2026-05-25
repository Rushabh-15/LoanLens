FOIR_THRESHOLD = 0.50
MINIMUM_MONTHLY_INCOME = 15000
LOAN_INCOME_MULTIPLE = 20


def calculate_emi(
    principal: float,
    annual_rate: float,
    tenure_months: int
) -> float:
    """
    Return monthly EMI using the standard amortization formula.
    Handles 0% interest by returning principal / tenure_months.
    """

    if tenure_months <= 0:
        raise ValueError("Tenure months must be greater than zero")

    if annual_rate == 0:
        return principal / tenure_months

    monthly_rate = annual_rate / 12 / 100

    growth_factor = (1 + monthly_rate) ** tenure_months

    emi = (
        principal
        * monthly_rate
        * growth_factor
        / (growth_factor - 1)
    )

    return emi


def calculate_foir(
    existing_emis: float,
    new_emi: float,
    monthly_income: float
) -> float:
    """
    Return FOIR as total monthly obligations divided by income.
    Raises ValueError when monthly_income is zero or negative.
    """

    if monthly_income <= 0:
        raise ValueError("Monthly income must be greater than zero")

    return (existing_emis + new_emi) / monthly_income


def evaluate_risk_flags(
    monthly_income: float | None,
    existing_emis: float | None,
    requested_loan_amount: float | None,
    tenure_months: int | None,
    foir: float | None
) -> list[str]:
    """
    Return a list of loan application risk flags.
    Returns an empty list for clean applications.
    """

    flags = []

    required_fields = [
        monthly_income,
        existing_emis,
        requested_loan_amount,
        tenure_months,
        foir
    ]

    if any(value is None for value in required_fields):
        flags.append("MISSING_CRITICAL_FIELD")
        return flags

    if monthly_income <= 0 or tenure_months <= 0:
        flags.append("MISSING_CRITICAL_FIELD")
        return flags

    if foir > FOIR_THRESHOLD:
        flags.append("FOIR_TOO_HIGH")

    if monthly_income < MINIMUM_MONTHLY_INCOME:
        flags.append("INCOME_BELOW_MINIMUM")

    if requested_loan_amount > (
        monthly_income * LOAN_INCOME_MULTIPLE
    ):
        flags.append("AMOUNT_DISPROPORTIONATE")

    return flags