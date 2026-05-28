from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.schemas import (
    ApplicantData,
    DecisionResponse,
    RiskMetrics,
)
from app.models.db_models import Application
from app.services.analysis import analyze_applicant

router = APIRouter()


@router.post(
    "/api/v1/applications/analyze-fields",
    response_model=DecisionResponse
)
def analyze_application_fields(
    applicant: ApplicantData,
    session: Session = Depends(get_session)
) -> DecisionResponse:
    """
    Analyze applicant data → persist result → return response
    """

    # 1. BUSINESS LOGIC
    result = analyze_applicant(applicant.model_dump())

    # 2. DB PERSISTENCE
    db_row = Application(
        extracted_fields={
            "applicant_data": applicant.model_dump(),
            "confidence_note": "N/A - human input"
        },
        emi=result.emi,
        foir=result.foir,
        risk_flags=result.risk_flags,
        decision=result.decision,
        reason=result.reason,
        status="processed"
    )

    try:
        session.add(db_row)
        session.commit()
        session.refresh(db_row)

    except Exception:
        session.rollback()
        raise

    # 3. API RESPONSE
    return DecisionResponse(
        decision=result.decision,
        reason=result.reason,
        applicant=applicant,
        metrics=RiskMetrics(
            estimated_emi=result.emi,
            foir=result.foir,
            risk_flags=result.risk_flags
        )
    )