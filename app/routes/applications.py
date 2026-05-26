from fastapi import APIRouter

from app.models.schemas import(
    ApplicantData,
    DecisionResponse,
    RiskMetrics,
)

from app.services.rules_engine import (
    calculate_emi,
    calculate_foir,
    evaluate_risk_flags
)

from app.services.decision import route_decision

router = APIRouter()

ASSUMED_ANNUAL_RATE = 12.0

@router.post(
    "/api/v1/applications/analyze-fields",
    response_model = DecisionResponse
)

def analyze_application_fields(
    applicant: ApplicantData
) -> DecisionResponse:
    """
    Analyze applicant financial data and return risk metrics.
    """

    estimated_emi = calculate_emi(
        principal=applicant.requested_amount,
        annual_rate=ASSUMED_ANNUAL_RATE,
        tenure_months=applicant.tenure_months
    )

    foir = calculate_foir(
        existing_emis=applicant.existing_emis,
        new_emi=estimated_emi,
        monthly_income=applicant.monthly_income
    )

    risk_flags = evaluate_risk_flags(
        monthly_income=applicant.monthly_income,
        existing_emis=applicant.existing_emis,
        requested_loan_amount=applicant.requested_amount,
        tenure_months=applicant.tenure_months,
        foir=foir
    )

    decision, reason = route_decision(
        risk_flags=risk_flags,
        has_low_confidence=False
    )

    metrics = RiskMetrics(
        estimated_emi=estimated_emi,
        foir=foir,
        risk_flags=risk_flags
    )

    return DecisionResponse(
        decision=decision,
        reason=reason,
        applicant=applicant,
        metrics=metrics
    )