from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.db_models import Application
from app.models.schemas import (
    ApplicantData,
    DecisionResponse,
    ExtractionDecisionResponse,
    RiskMetrics,
    DecisionType,
)
from app.services.analysis import analyze_applicant
from app.services.pdf_extractor import (
    extract_text_from_pdf,
    NoExtractableTextError,
)
from app.services.llm_extractor import extract_fields
from app.services.confidence import has_low_confidence

router = APIRouter()


@router.post(
    "/api/v1/applications/analyze-fields",
    response_model=DecisionResponse,
)
def analyze_application_fields(
    applicant: ApplicantData,
    session: Session = Depends(get_session),
) -> DecisionResponse:
    result = analyze_applicant(applicant.model_dump())

    status = (
        "needs_review"
        if result.decision == DecisionType.NEEDS_REVIEW
        else "processed"
    )

    db_row = Application(
        extracted_fields={
            "source": "human_input",
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

    try:
        session.add(db_row)
        session.commit()
        session.refresh(db_row)
    except Exception:
        session.rollback()
        raise

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


@router.post(
    "/api/v1/applications/analyze",
    response_model=ExtractionDecisionResponse,
)
async def analyze_application_upload(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ExtractionDecisionResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF",
        )

    data = await file.read()

    if data[:5] != b"%PDF-":
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF",
        )

    try:
        text = extract_text_from_pdf(data)
    except NoExtractableTextError:
        raise HTTPException(
            status_code=422,
            detail="PDF contains no extractable text",
        )

    extracted = extract_fields(text)
    low_conf = has_low_confidence(extracted)

    applicant_data = {
        "name": extracted.name.value,
        "age": extracted.age.value,
        "employment_type": extracted.employment_type.value,
        "employer": extracted.employer.value,
        "monthly_income": extracted.monthly_income.value,
        "existing_emis": extracted.existing_emis.value,
        "requested_amount": extracted.requested_amount.value,
        "tenure_months": extracted.tenure_months.value,
        "purpose": extracted.purpose.value,
    }

    if low_conf:
        decision = DecisionType.NEEDS_REVIEW
        reason = (
            "Low-confidence extraction; "
            "routed to human review."
        )
        emi = 0.0
        foir = 0.0
        risk_flags = ["MISSING_CRITICAL_FIELD"]
    else:
        result = analyze_applicant(
            applicant_data,
            has_low_confidence=False,
        )

        decision = result.decision
        reason = result.reason
        emi = result.emi
        foir = result.foir
        risk_flags = result.risk_flags

    status = (
        "needs_review"
        if decision == DecisionType.NEEDS_REVIEW
        else "processed"
    )

    db_row = Application(
        extracted_fields={
            "source": "pdf_extraction",
            "filename": file.filename,
            "fields": extracted.model_dump(),
        },
        emi=emi,
        foir=foir,
        risk_flags=risk_flags,
        decision=decision.value,
        reason=reason,
        status=status,
    )

    try:
        session.add(db_row)
        session.commit()
        session.refresh(db_row)
    except Exception:
        session.rollback()
        raise

    return ExtractionDecisionResponse(
        decision=decision,
        reason=reason,
        extracted_fields=extracted,
        low_confidence=low_conf,
        metrics=RiskMetrics(
            estimated_emi=emi,
            foir=foir,
            risk_flags=risk_flags,
        ),
    )