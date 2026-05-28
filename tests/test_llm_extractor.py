import pytest

from app.services.llm_extractor import extract_fields

from app.models.schemas import (
    ExtractedFields,
    StringField,
    IntField,
    FloatField,
    Confidence,
)


# -----------------------------
# TEST 1: Successful extraction
# -----------------------------
def test_extract_fields_success(monkeypatch):

    def fake_call(_):
        return ExtractedFields(
            name=StringField(
                value="Rahul Sharma",
                confidence=Confidence.high,
            ),
            age=IntField(
                value=30,
                confidence=Confidence.high,
            ),
            employment_type=StringField(
                value="salaried",
                confidence=Confidence.high,
            ),
            employer=StringField(
                value="Infosys",
                confidence=Confidence.high,
            ),
            monthly_income=FloatField(
                value=60000,
                confidence=Confidence.high,
            ),
            existing_emis=FloatField(
                value=25000,
                confidence=Confidence.high,
            ),
            requested_amount=FloatField(
                value=500000,
                confidence=Confidence.high,
            ),
            tenure_months=IntField(
                value=60,
                confidence=Confidence.high,
            ),
            purpose=StringField(
                value="Car loan",
                confidence=Confidence.high,
            ),
        )

    monkeypatch.setattr(
        "app.services.llm_extractor._call_claude",
        fake_call,
    )

    result = extract_fields("dummy pdf text")

    assert result.name.value == "Rahul Sharma"
    assert result.monthly_income.value == 60000
    assert result.tenure_months.value == 60


# -----------------------------------------
# TEST 2: Missing / low confidence fields
# -----------------------------------------
def test_extract_fields_missing_fields(monkeypatch):

    def fake_call(_):
        return ExtractedFields.all_low()

    monkeypatch.setattr(
        "app.services.llm_extractor._call_claude",
        fake_call,
    )

    result = extract_fields("irrelevant text")

    assert result.monthly_income.value is None
    assert result.monthly_income.confidence == Confidence.low

    assert result.name.value is None
    assert result.name.confidence == Confidence.low


# -----------------------------------------
# TEST 3: API failure fallback
# -----------------------------------------
def test_extract_fields_api_failure(monkeypatch):

    def fake_call(_):
        raise Exception("API failure")

    monkeypatch.setattr(
        "app.services.llm_extractor._call_claude",
        fake_call,
    )

    result = extract_fields("any text")

    # fallback should never crash pipeline
    assert result.name.value is None
    assert result.age.value is None
    assert result.monthly_income.value is None
    assert result.tenure_months.value is None

    # confidence should be low everywhere
    assert result.name.confidence == Confidence.low
    assert result.monthly_income.confidence == Confidence.low