import io

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.main import app
from app.db import SessionLocal
from app.models.db_models import Application
from app.models.schemas import (
    Confidence,
    ExtractedFields,
    StringField,
    IntField,
    FloatField,
)
from app.services import llm_extractor


def make_text_pdf() -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)

    pdf.drawString(100, 750, "Name: Aarav Mehta")
    pdf.drawString(100, 730, "Age: 29")
    pdf.drawString(100, 710, "Employment Type: salaried")
    pdf.drawString(100, 690, "Employer: TCS")
    pdf.drawString(100, 670, "Monthly Income: 90000")
    pdf.drawString(100, 650, "Existing EMIs: 5000")
    pdf.drawString(100, 630, "Requested Amount: 300000")
    pdf.drawString(100, 610, "Tenure Months: 24")
    pdf.drawString(100, 590, "Purpose: home renovation")

    pdf.save()
    return buffer.getvalue()


def make_blank_pdf() -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def all_high_extracted_fields() -> ExtractedFields:
    return ExtractedFields(
        name=StringField(value="Aarav Mehta", confidence=Confidence.high),
        age=IntField(value=29, confidence=Confidence.high),
        employment_type=StringField(value="salaried", confidence=Confidence.high),
        employer=StringField(value="TCS", confidence=Confidence.high),
        monthly_income=FloatField(value=90000, confidence=Confidence.high),
        existing_emis=FloatField(value=5000, confidence=Confidence.high),
        requested_amount=FloatField(value=300000, confidence=Confidence.high),
        tenure_months=IntField(value=24, confidence=Confidence.high),
        purpose=StringField(value="home renovation", confidence=Confidence.high),
    )


def low_confidence_extracted_fields() -> ExtractedFields:
    fields = all_high_extracted_fields()
    fields.monthly_income.confidence = Confidence.low
    return fields


def missing_value_extracted_fields() -> ExtractedFields:
    fields = all_high_extracted_fields()
    fields.monthly_income.value = None
    fields.monthly_income.confidence = Confidence.low
    return fields


def count_applications() -> int:
    with SessionLocal() as session:
        return session.query(Application).count()


def test_upload_pdf_happy_path_persists_row(monkeypatch):
    def fake_call_claude(raw_text: str) -> ExtractedFields:
        return all_high_extracted_fields()

    monkeypatch.setattr(
        llm_extractor,
        "_call_claude",
        fake_call_claude,
    )

    with TestClient(app) as client:
        before_count = count_applications()

        response = client.post(
            "/api/v1/applications/analyze",
            files={
                "file": (
                    "sample_application.pdf",
                    make_text_pdf(),
                    "application/pdf",
                )
            },
        )

        after_count = count_applications()

    assert response.status_code == 200

    body = response.json()

    assert "decision" in body
    assert "metrics" in body
    assert "extracted_fields" in body
    assert after_count == before_count + 1


def test_upload_pdf_low_confidence_goes_to_review(monkeypatch):
    def fake_call_claude(raw_text: str) -> ExtractedFields:
        return low_confidence_extracted_fields()

    monkeypatch.setattr(
        llm_extractor,
        "_call_claude",
        fake_call_claude,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/applications/analyze",
            files={
                "file": (
                    "sample_application.pdf",
                    make_text_pdf(),
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["decision"] == "needs_review"
    assert body["low_confidence"] is True

    # Low confidence alone should not invent a missing-field flag.
    # Values are present, so metrics should still be honestly computed.
    assert body["metrics"]["risk_flags"] == []
    assert body["metrics"]["estimated_emi"] > 0
    assert body["metrics"]["foir"] > 0
    assert body["reason_codes"] == ["LOW_CONFIDENCE:monthly_income"]


def test_upload_pdf_missing_value_goes_to_review(monkeypatch):
    def fake_call_claude(raw_text: str) -> ExtractedFields:
        return missing_value_extracted_fields()

    monkeypatch.setattr(
        llm_extractor,
        "_call_claude",
        fake_call_claude,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/applications/analyze",
            files={
                "file": (
                    "sample_application.pdf",
                    make_text_pdf(),
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["decision"] == "needs_review"
    assert body["low_confidence"] is True
    assert body["metrics"]["estimated_emi"] == 0.0
    assert body["metrics"]["foir"] == 0.0
    assert body["metrics"]["risk_flags"] == ["MISSING_CRITICAL_FIELD"]
    # One code per field: missing outranks low confidence for monthly_income.
    assert body["reason_codes"] == ["MISSING_VALUE:monthly_income"]

def test_upload_non_pdf_returns_400():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/applications/analyze",
            files={
                "file": (
                    "not_a_pdf.txt",
                    b"hello world",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "File must be a PDF"


def test_upload_blank_pdf_returns_422():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/applications/analyze",
            files={
                "file": (
                    "blank.pdf",
                    make_blank_pdf(),
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "PDF contains no extractable text"


def test_unknown_application_id_returns_404():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/applications/999999999"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Application not found"


def test_review_queue_returns_needs_review_application(monkeypatch):
    def fake_call_claude(raw_text: str) -> ExtractedFields:
        return low_confidence_extracted_fields()

    monkeypatch.setattr(
        llm_extractor,
        "_call_claude",
        fake_call_claude,
    )

    with TestClient(app) as client:
        upload_response = client.post(
            "/api/v1/applications/analyze",
            files={
                "file": (
                    "sample_application.pdf",
                    make_text_pdf(),
                    "application/pdf",
                )
            },
        )

        queue_response = client.get("/api/v1/review-queue")

    assert upload_response.status_code == 200
    assert queue_response.status_code == 200

    queue = queue_response.json()

    assert len(queue) >= 1
    assert any(
        item["status"] == "needs_review"
        for item in queue
    )


# -----------------------------------------
# B2: reason codes and critical-field review
# -----------------------------------------
def upload_pdf(client: TestClient):
    return client.post(
        "/api/v1/applications/analyze",
        files={
            "file": (
                "sample_application.pdf",
                make_text_pdf(),
                "application/pdf",
            )
        },
    )


def fake_extraction(monkeypatch, fields: ExtractedFields) -> None:
    monkeypatch.setattr(llm_extractor, "_call_claude", lambda raw_text: fields)


def test_low_confidence_on_non_critical_field_stays_eligible(monkeypatch):
    # Behaviour change in B2: a low purpose used to send the case to review.
    fields = all_high_extracted_fields()
    fields.purpose.confidence = Confidence.low
    fake_extraction(monkeypatch, fields)

    with TestClient(app) as client:
        response = upload_pdf(client)

    assert response.status_code == 200
    body = response.json()

    assert body["decision"] == "eligible"
    assert body["low_confidence"] is False
    assert body["reason_codes"] == []


def test_reason_codes_are_returned_stored_and_listed_in_review_queue(monkeypatch):
    fake_extraction(monkeypatch, low_confidence_extracted_fields())

    with TestClient(app) as client:
        body = upload_pdf(client).json()
        record = client.get(f"/api/v1/applications/{body['application_id']}").json()
        queue = client.get("/api/v1/review-queue").json()

    expected = ["LOW_CONFIDENCE:monthly_income"]

    assert body["reason_codes"] == expected
    assert record["reason_codes"] == expected

    queued = [item for item in queue if item["id"] == body["application_id"]]
    assert len(queued) == 1
    assert queued[0]["reason_codes"] == expected


def test_analyze_fields_returns_and_stores_decline_codes():
    # FOIR = (5,000 + 19,928.59) / 30,000 = 0.83, over the 0.50 limit.
    applicant = {
        "name": "Aarav Mehta",
        "age": 29,
        "employment_type": "salaried",
        "employer": "TCS",
        "monthly_income": 30000,
        "existing_emis": 5000,
        "requested_amount": 600000,
        "tenure_months": 36,
        "purpose": "home renovation",
    }

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/applications/analyze-fields",
            json=applicant,
        )

    assert response.status_code == 200
    body = response.json()

    assert body["decision"] == "decline"
    assert body["reason_codes"] == ["FOIR_TOO_HIGH"]

    with SessionLocal() as session:
        latest = session.query(Application).order_by(Application.id.desc()).first()

    assert latest.reason_codes == ["FOIR_TOO_HIGH"]


def test_row_created_without_reason_codes_stores_an_empty_list():
    # scripts/test_db.py builds rows like this; default=list keeps it working.
    with TestClient(app):
        with SessionLocal() as session:
            row = Application(
                extracted_fields={},
                emi=0.0,
                foir=0.0,
                risk_flags=[],
                decision="eligible",
                reason="Passed all checks.",
                status="processed",
            )
            session.add(row)
            session.commit()
            session.refresh(row)

            assert row.reason_codes == []