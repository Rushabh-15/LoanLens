import io

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.main import app
from app.models.schemas import Confidence, DecisionType, ExtractedFields
from app.services import llm_extractor


@pytest.mark.parametrize(
    "field_name",
    ["age", "monthly_income", "existing_emis", "requested_amount", "tenure_months"],
)
@pytest.mark.parametrize(
    "field_value", [0, -1, None], ids=["zero", "negative", "missing"]
)
def test_numeric_extracted_values_never_return_500(
    monkeypatch, field_name, field_value
):
    applicant = {
        "name": "Aarav Mehta",
        "age": 29,
        "employment_type": "salaried",
        "employer": "TCS",
        "monthly_income": 90000,
        "existing_emis": 5000,
        "requested_amount": 600000,
        "tenure_months": 36,
        "purpose": "home renovation",
    }
    applicant[field_name] = field_value

    extracted = ExtractedFields.model_validate(
        {
            name: {"value": value, "confidence": Confidence.high}
            for name, value in applicant.items()
        }
    )

    def fake_call_claude(raw_text):
        return extracted

    monkeypatch.setattr(llm_extractor, "_call_claude", fake_call_claude)

    # Create a real PDF; only the Claude call is mocked.
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for index, (name, value) in enumerate(applicant.items()):
        pdf.drawString(72, 750 - index * 20, f"{name}: {value}")
    pdf.save()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/applications/analyze",
            files={"file": ("guard.pdf", buffer.getvalue(), "application/pdf")},
        )

    assert response.status_code == 200, (
        f"{field_name}={field_value!r}: "
        f"HTTP {response.status_code}: {response.text}"
    )

    body = response.json()
    assert body["low_confidence"] is False
    assert body["extracted_fields"] == extracted.model_dump(mode="json")

    if field_name == "existing_emis" and field_value == 0:
        # Having no existing EMIs is valid.
        assert body["decision"] == DecisionType.ELIGIBLE.value
        assert body["metrics"]["risk_flags"] == []
    else:
        assert body["decision"] == DecisionType.NEEDS_REVIEW.value
        expected_flag = (
            "MISSING_CRITICAL_FIELD" if field_value is None else "INVALID_VALUE"
        )
        assert body["metrics"]["risk_flags"] == [expected_flag]
