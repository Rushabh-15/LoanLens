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