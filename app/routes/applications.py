from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.db_models import Application
from app.models.schemas import (
    ApplicantData,
    ApplicationRecordResponse,
    DecisionResponse,
    ExtractionDecisionResponse,
    RiskMetrics,
    DecisionType,
    StatusType,
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
        StatusType.NEEDS_REVIEW
        if result.decision == DecisionType.NEEDS_REVIEW
        else StatusType.PROCESSED
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
        status=status.value,
    )

    try:
        session.add(db_row)
        session.commit()
        session.refresh(db_row)
    except Exception:
        session.rollback()
        raise

    return DecisionResponse(
        decision=result.decision,
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

    result = analyze_applicant(
        applicant_data,
        has_low_confidence=low_conf,
    )

    status = (
        StatusType.NEEDS_REVIEW
        if result.decision == DecisionType.NEEDS_REVIEW
        else StatusType.PROCESSED
    )

    db_row = Application(
        extracted_fields={
            "source": "pdf_extraction",
            "filename": file.filename,
            "fields": extracted.model_dump(),
        },
        emi=result.emi,
        foir=result.foir,
        risk_flags=result.risk_flags,
        decision=result.decision.value,
        reason=result.reason,
        status=status.value,
    )

    try:
        session.add(db_row)
        session.commit()
        session.refresh(db_row)
    except Exception:
        session.rollback()
        raise

    return ExtractionDecisionResponse(
        application_id=db_row.id,
        decision=result.decision,
        reason=result.reason,
        extracted_fields=extracted,
        low_confidence=low_conf,
        metrics=RiskMetrics(
            estimated_emi=result.emi,
            foir=result.foir,
            risk_flags=result.risk_flags,
        ),
    )


@router.get(
    "/api/v1/applications/{application_id}",
    response_model=ApplicationRecordResponse,
)
def get_application(
    application_id: int,
    session: Session = Depends(get_session),
) -> ApplicationRecordResponse:
    application = session.get(Application, application_id)

    if application is None:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return application


@router.get(
    "/api/v1/review-queue",
    response_model=list[ApplicationRecordResponse],
)
def get_review_queue(
    session: Session = Depends(get_session),
) -> list[ApplicationRecordResponse]:
    applications = session.scalars(
        select(Application).where(
            Application.status == StatusType.NEEDS_REVIEW.value
        )
    ).all()

    return applications