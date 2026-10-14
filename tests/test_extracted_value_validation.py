import io

import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from app.main import app
from app.models.schemas import Confidence, DecisionType, ExtractedFields
from app.services import analysis, llm_extractor
from app.services.analysis import analyze_applicant


NUMERIC_FIELDS = (
    "age",
    "monthly_income",
    "existing_emis",
    "requested_amount",
    "tenure_months",
)


INVALID_CASES = [
    pytest.param(
        {"age": 16},
        ["INVALID_VALUE"],
        False,
        "Invalid value for age; routed to human review.",
        id="age_under_18",
    ),
    pytest.param(
        {"age": None},
        ["MISSING_CRITICAL_FIELD"],
        False,
        "Missing value for age; routed to human review.",
        id="age_missing",
    ),
    pytest.param(
        {"monthly_income": 0},
        ["INVALID_VALUE"],
        False,
        "Invalid value for monthly_income; routed to human review.",
        id="income_zero",
    ),
    pytest.param(
        {"monthly_income": -5000},
        ["INVALID_VALUE"],
        False,
        "Invalid value for monthly_income; routed to human review.",
        id="income_negative",
    ),
    pytest.param(
        {"tenure_months": 0},
        ["INVALID_VALUE"],
        False,
        "Invalid value for tenure_months; routed to human review.",
        id="tenure_zero",
    ),
    pytest.param(
        {"tenure_months": -1},
        ["INVALID_VALUE"],
        False,
        "Invalid value for tenure_months; routed to human review.",
        id="tenure_negative",
    ),
    pytest.param(
        {"requested_amount": 0},
        ["INVALID_VALUE"],
        False,
        "Invalid value for requested_amount; routed to human review.",
        id="requested_amount_zero",
    ),
    pytest.param(
        {"requested_amount": -600000},
        ["INVALID_VALUE"],
        False,
        "Invalid value for requested_amount; routed to human review.",
        id="requested_amount_negative",
    ),
    pytest.param(
        {"existing_emis": -50000, "requested_amount": 1500000},
        ["INVALID_VALUE"],
        False,
        "Invalid value for existing_emis; routed to human review.",
        id="existing_emis_negative",
    ),
    pytest.param(
        {"age": 16, "monthly_income": 0},
        ["INVALID_VALUE"],
        False,
        "Invalid values for age, monthly_income; routed to human review.",
        id="multiple_invalid_values",
    ),
    pytest.param(
        {"age": None, "tenure_months": None},
        ["MISSING_CRITICAL_FIELD"],
        False,
        "Missing values for age, tenure_months; routed to human review.",
        id="multiple_missing_values",
    ),
    pytest.param(
        {"age": None, "monthly_income": -5000},
        ["MISSING_CRITICAL_FIELD", "INVALID_VALUE"],
        False,
        "Missing value for age; Invalid value for monthly_income; "
        "routed to human review.",
        id="missing_and_invalid_values",
    ),
    pytest.param(
        {"age": 16},
        ["INVALID_VALUE"],
        True,
        "Invalid value for age; low-confidence extraction; "
        "routed to human review.",
        id="invalid_value_with_low_confidence",
    ),
]


@pytest.fixture
def valid_applicant() -> dict:
    """Return a fresh valid applicant for each test."""
    return {
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


@pytest.fixture
def forbid_financial_calculations(monkeypatch):
    """Fail if missing or invalid inputs reach EMI or FOIR calculations."""

    def unexpected_calculation(*args, **kwargs):
        pytest.fail("Missing or invalid inputs reached EMI/FOIR calculations.")

    monkeypatch.setattr(analysis, "calculate_emi", unexpected_calculation)
    monkeypatch.setattr(analysis, "calculate_foir", unexpected_calculation)


def make_text_pdf(applicant_data: dict) -> bytes:
    """Create a real PDF for the API tests."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)

    for index, (field_name, value) in enumerate(applicant_data.items()):
        pdf.drawString(72, 750 - index * 20, f"{field_name}: {value}")

    pdf.save()
    return buffer.getvalue()


@pytest.mark.parametrize(
    "overrides, expected_flags, low_confidence, expected_reason",
    INVALID_CASES,
)
def test_analyze_applicant_invalid_values_need_review(
    valid_applicant,
    overrides,
    expected_flags,
    low_confidence,
    expected_reason,
    forbid_financial_calculations,
):
    applicant_data = {**valid_applicant, **overrides}

    result = analyze_applicant(
        applicant_data,
        has_low_confidence=low_confidence,
    )

    assert result.decision == DecisionType.NEEDS_REVIEW
    assert result.risk_flags == expected_flags
    assert result.reason == expected_reason


@pytest.mark.parametrize("field_name", NUMERIC_FIELDS)
def test_omitted_critical_key_needs_review(
    valid_applicant,
    field_name,
    forbid_financial_calculations,
):
    valid_applicant.pop(field_name)

    result = analyze_applicant(
        valid_applicant,
        has_low_confidence=False,
    )

    assert result.decision == DecisionType.NEEDS_REVIEW
    assert result.risk_flags == ["MISSING_CRITICAL_FIELD"]
    assert result.reason == (
        f"Missing value for {field_name}; routed to human review."
    )


def test_age_18_and_zero_existing_emis_are_valid(valid_applicant):
    valid_applicant.update(age=18, existing_emis=0)

    result = analyze_applicant(
        valid_applicant,
        has_low_confidence=False,
    )

    assert result.decision == DecisionType.ELIGIBLE
    assert result.risk_flags == []
    assert result.emi > 0
    assert result.foir > 0


@pytest.mark.parametrize(
    "overrides, expected_flags, low_confidence, expected_reason",
    INVALID_CASES,
)
def test_upload_invalid_extracted_values_need_review(
    monkeypatch,
    valid_applicant,
    overrides,
    expected_flags,
    low_confidence,
    expected_reason,
):
    applicant_data = {**valid_applicant, **overrides}

    confidence = Confidence.low if low_confidence else Confidence.high
    extracted = ExtractedFields.model_validate(
        {
            field_name: {
                "value": value,
                "confidence": confidence,
            }
            for field_name, value in applicant_data.items()
        }
    )

    claude_calls = []

    def fake_call_claude(raw_text: str) -> ExtractedFields:
        claude_calls.append(raw_text)
        return extracted

    monkeypatch.setattr(llm_extractor, "_call_claude", fake_call_claude)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/applications/analyze",
            files={
                "file": (
                    "invalid_application.pdf",
                    make_text_pdf(applicant_data),
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 200, response.text
        body = response.json()

        record_response = client.get(
            f"/api/v1/applications/{body['application_id']}"
        )

    assert len(claude_calls) == 1
    assert claude_calls[0].strip(), (
        "The PDF reader must supply nonempty text."
    )

    # Ensure extraction did not silently fall back to all_low().
    assert body["low_confidence"] is low_confidence
    assert body["extracted_fields"] == extracted.model_dump(mode="json")

    assert body["decision"] == DecisionType.NEEDS_REVIEW.value
    assert body["metrics"]["risk_flags"] == expected_flags
    assert body["reason"] == expected_reason

    assert record_response.status_code == 200
    assert record_response.json()["reason"] == expected_reason
