from dataclasses import dataclass

from app.models.schemas import DecisionType

from app.services.rules_engine import (
    calculate_emi,
    calculate_foir,
    evaluate_risk_flags,
)

from app.services.decision import route_decision


@dataclass
class AnalysisResult:
    emi: float
    foir: float
    risk_flags: list[str]
    decision: DecisionType
    reason: str


def analyze_applicant(
    applicant_data: dict,
    has_low_confidence: bool = False,
) -> AnalysisResult:
    """
    Pure business logic orchestration layer.

    This service composes already-tested
    underwriting functions.

    No FastAPI.
    No database.
    No HTTP concerns.
    """

    monthly_income = applicant_data["monthly_income"]
    existing_emis = applicant_data["existing_emis"]
    requested_amount = applicant_data["requested_amount"]
    tenure_months = applicant_data["tenure_months"]

    # Default interest rate for prototype
    annual_interest_rate = applicant_data.get(
        "annual_interest_rate",
        12.0,
    )

    # EMI calculation
    emi = calculate_emi(
        principal=requested_amount,
        annual_rate=annual_interest_rate,
        tenure_months=tenure_months,
    )

    # FOIR calculation
    foir = calculate_foir(
        existing_emis=existing_emis,
        new_emi=emi,
        monthly_income=monthly_income,
    )

    # Risk evaluation
    risk_flags = evaluate_risk_flags(
        monthly_income=monthly_income,
        existing_emis=existing_emis,
        requested_loan_amount=requested_amount,
        tenure_months=tenure_months,
        foir=foir,
    )

    # Decision routing
    decision, reason = route_decision(
        risk_flags=risk_flags,
        has_low_confidence=has_low_confidence,
    )

    return AnalysisResult(
        emi=emi,
        foir=foir,
        risk_flags=risk_flags,
        decision=decision,
        reason=reason,
    )