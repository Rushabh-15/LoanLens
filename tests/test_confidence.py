from app.models.schemas import (
    Confidence,
    ExtractedFields,
    FloatField,
    IntField,
    StringField,
)

from app.services.confidence import has_low_confidence


def test_all_high_confidence_returns_false():
    fields = ExtractedFields(
        name=StringField(
            value="Rahul",
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
            value=5000,
            confidence=Confidence.high,
        ),
        requested_amount=FloatField(
            value=200000,
            confidence=Confidence.high,
        ),
        tenure_months=IntField(
            value=60,
            confidence=Confidence.high,
        ),
        purpose=StringField(
            value="Car",
            confidence=Confidence.high,
        ),
    )

    assert has_low_confidence(fields) is False


def test_one_low_confidence_returns_true():
    fields = ExtractedFields(
        name=StringField(
            value="Rahul",
            confidence=Confidence.high,
        ),
        age=IntField(
            value=30,
            confidence=Confidence.low,
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
            value=5000,
            confidence=Confidence.high,
        ),
        requested_amount=FloatField(
            value=200000,
            confidence=Confidence.high,
        ),
        tenure_months=IntField(
            value=60,
            confidence=Confidence.high,
        ),
        purpose=StringField(
            value="Car",
            confidence=Confidence.high,
        ),
    )

    assert has_low_confidence(fields) is True


def test_mixed_confidence_returns_true():

    fields = ExtractedFields(
        name=StringField(value="Rahul", confidence=Confidence.high),
        age=IntField(value=30, confidence=Confidence.high),
        employment_type=StringField(
            value="salaried",
            confidence=Confidence.high
        ),
        employer=StringField(
            value="Infosys",
            confidence=Confidence.high
        ),

        # Missing income → low confidence
        monthly_income=FloatField(
            value=None,
            confidence=Confidence.low
        ),

        existing_emis=FloatField(
            value=5000,
            confidence=Confidence.high
        ),

        requested_amount=FloatField(
            value=200000,
            confidence=Confidence.high
        ),

        tenure_months=IntField(
            value=60,
            confidence=Confidence.high
        ),

        purpose=StringField(
            value="Car",
            confidence=Confidence.high
        ),
    )

    assert has_low_confidence(fields) is True

def test_all_medium_confidence_returns_false():

    fields = ExtractedFields(
        name=StringField(value="Rahul", confidence=Confidence.medium),
        age=IntField(value=30, confidence=Confidence.medium),
        employment_type=StringField(
            value="salaried",
            confidence=Confidence.medium
        ),
        employer=StringField(
            value="Infosys",
            confidence=Confidence.medium
        ),
        monthly_income=FloatField(
            value=60000,
            confidence=Confidence.medium
        ),
        existing_emis=FloatField(
            value=5000,
            confidence=Confidence.medium
        ),
        requested_amount=FloatField(
            value=200000,
            confidence=Confidence.medium
        ),
        tenure_months=IntField(
            value=60,
            confidence=Confidence.medium
        ),
        purpose=StringField(
            value="Car",
            confidence=Confidence.medium
        ),
    )

    assert has_low_confidence(fields) is False