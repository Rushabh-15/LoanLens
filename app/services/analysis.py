from dataclasses import dataclass


@dataclass
class AnalysisResult:
    emi: float
    foir: float
    risk_flags: list[str]
    decision: str
    reason: str


def analyze_applicant(applicant_data: dict) -> AnalysisResult:
    """
    Pure business logic layer.

    Input:
        applicant data dictionary

    Output:
        underwriting analysis result

    No FastAPI.
    No database.
    No HTTP concerns.
    """

    monthly_income = applicant_data["monthly_income"]
    existing_emis = applicant_data["existing_emis"]
    requested_loan_amount = applicant_data["requested_amount"]
    tenure_months = applicant_data["tenure_months"]
    annual_interest_rate = 12

    # Convert annual % rate → monthly decimal
    monthly_interest_rate = annual_interest_rate / 12 / 100

    # EMI Calculation
    if monthly_interest_rate == 0:
        emi = requested_loan_amount / tenure_months

    else:
        emi = (
            requested_loan_amount
            * monthly_interest_rate
            * (1 + monthly_interest_rate) ** tenure_months
        ) / (
            (1 + monthly_interest_rate) ** tenure_months - 1
        )

    emi = round(emi, 2)

    # FOIR Calculation
    total_monthly_obligations = existing_emis + emi

    foir = total_monthly_obligations / monthly_income

    foir = round(foir, 2)

    # Risk Flags
    risk_flags = []

    if foir > 0.5:
        risk_flags.append("high_foir")

    if monthly_income < 30000:
        risk_flags.append("low_income")

    # Decision Logic
    if foir >= 0.7:
        decision = "decline"
        reason = "FOIR too high"

    elif foir >= 0.5:
        decision = "needs_review"
        reason = "Borderline FOIR"

    else:
        decision = "eligible"
        reason = "Acceptable FOIR"

    return AnalysisResult(
        emi=emi,
        foir=foir,
        risk_flags=risk_flags,
        decision=decision,
        reason=reason,
    )