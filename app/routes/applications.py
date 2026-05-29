from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.db_models import Application
from app.models.schemas import (
    ApplicantData,
    DecisionResponse,
    RiskMetrics,
    DecisionType,
)
from app.services.analysis import analyze_applicant

router = APIRouter()


@router.post(
    "/api/v1/applications/analyze-fields",
    response_model=DecisionResponse,
)
def analyze_application_fields(
    applicant: ApplicantData,
    session: Session = Depends(get_session),
) -> DecisionResponse:
    """
    Analyze applicant data,
    persist the result,
    and return the underwriting decision.
    """

    # -----------------------------
    # 1. Run business analysis
    # -----------------------------
    result = analyze_applicant(
        applicant.model_dump()
    )

    # -----------------------------
    # 2. Determine workflow status
    # -----------------------------
    status = (
        "needs_review"
        if result.decision == DecisionType.NEEDS_REVIEW
        else "processed"
    )

    # -----------------------------
    # 3. Create DB row
    # -----------------------------
    db_row = Application(
        extracted_fields={
            "applicant_data": applicant.model_dump(),
            "confidence_note": "N/A - human input",
        },
        emi=result.emi,
        foir=result.foir,
        risk_flags=result.risk_flags,
        decision=result.decision.value,
        reason=result.reason,
        status=status,
    )

    # -----------------------------
    # 4. Persist safely
    # -----------------------------
    try:
        session.add(db_row)
        session.commit()
        session.refresh(db_row)

    except Exception:
        session.rollback()
        raise

    # -----------------------------
    # 5. Return API response
    # -----------------------------
    return DecisionResponse(
        decision=result.decision.value,
        reason=result.reason,
        applicant=applicant,
        metrics=RiskMetrics(
            estimated_emi=result.emi,
            foir=result.foir,
            risk_flags=result.risk_flags,
        ),
    )