import pytest

from app.models.schemas import Confidence, ExtractedFields
from app.services.confidence import low_confidence_fields
from app.services.decision import CRITICAL_FIELDS


# Fields the rules never read. Their confidence must not route a case.
NON_CRITICAL_FIELDS = ("name", "employment_type", "employer", "purpose")

VALID_VALUES = {
    "name": "Rahul Sharma",
    "age": 30,
    "employment_type": "salaried",
    "employer": "Infosys",
    "monthly_income": 60000,
    "existing_emis": 5000,
    "requested_amount": 200000,
    "tenure_months": 60,
    "purpose": "Car",
}


def extracted(default=Confidence.high, **overrides) -> ExtractedFields:
    """Build valid fields at one confidence level, overriding named fields."""
    return ExtractedFields.model_validate(
        {
            field_name: {
                "value": value,
                "confidence": overrides.get(field_name, default),
            }
            for field_name, value in VALID_VALUES.items()
        }
    )


def test_every_schema_field_is_classified_exactly_once():
    # Fails if someone adds a field to ExtractedFields without deciding
    # whether its confidence should route the case.
    critical = set(CRITICAL_FIELDS)
    non_critical = set(NON_CRITICAL_FIELDS)

    assert critical.isdisjoint(non_critical)
    assert critical | non_critical == set(ExtractedFields.model_fields)


def test_all_high_returns_no_fields():
    assert low_confidence_fields(extracted()) == []


@pytest.mark.parametrize("field_name", CRITICAL_FIELDS)
def test_low_critical_field_is_returned(field_name):
    fields = extracted(**{field_name: Confidence.low})

    assert low_confidence_fields(fields) == [field_name]


@pytest.mark.parametrize("field_name", NON_CRITICAL_FIELDS)
def test_low_non_critical_field_is_ignored(field_name):
    # Behaviour change in B2: this used to send the case to review.
    fields = extracted(**{field_name: Confidence.low})

    assert low_confidence_fields(fields) == []


def test_all_non_critical_fields_low_together_are_ignored():
    fields = extracted(**{name: Confidence.low for name in NON_CRITICAL_FIELDS})

    assert low_confidence_fields(fields) == []


def test_all_low_returns_critical_fields_in_order():
    assert low_confidence_fields(extracted(default=Confidence.low)) == list(
        CRITICAL_FIELDS
    )


def test_order_follows_critical_fields_not_schema_or_input():
    fields = extracted(tenure_months=Confidence.low, age=Confidence.low)

    assert low_confidence_fields(fields) == ["age", "tenure_months"]


def test_all_medium_returns_no_fields():
    # Medium is accepted until C2's accuracy-by-confidence table says otherwise.
    assert low_confidence_fields(extracted(default=Confidence.medium)) == []


def test_missing_value_labelled_low_is_returned():
    # Confidence is about the label. validate_inputs() separately reports the
    # missing value, and the router keeps only MISSING_VALUE for that field.
    fields = extracted()
    fields.monthly_income.value = None
    fields.monthly_income.confidence = Confidence.low

    assert low_confidence_fields(fields) == ["monthly_income"]