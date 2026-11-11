import dataclasses
from itertools import product

import pytest

from app.models.schemas import DecisionType, ExtractionStatus
from app.services.decision import CRITICAL_FIELDS, route_decision


REVIEW = DecisionType.NEEDS_REVIEW
DECLINE = DecisionType.DECLINE
ELIGIBLE = DecisionType.ELIGIBLE

FAILED = ["EXTRACTION_FAILED:timeout"]

# Inputs used whenever a condition is on:
#   failed  -> extraction_status=TIMEOUT
#   invalid -> invalid_fields=("age",)
#   low     -> low_confidence_fields=("monthly_income",)
#   decline -> decline_flags=("FOIR_TOO_HIGH",)
#
# failed, invalid, low, decline -> expected decision, expected reason codes
TRUTH_TABLE = [
    (False, False, False, False, ELIGIBLE, []),
    (False, False, False, True,  DECLINE,  ["FOIR_TOO_HIGH"]),
    (False, False, True,  False, REVIEW,   ["LOW_CONFIDENCE:monthly_income"]),
    (False, False, True,  True,  REVIEW,   ["LOW_CONFIDENCE:monthly_income"]),
    (False, True,  False, False, REVIEW,   ["INVALID_VALUE:age"]),
    (False, True,  False, True,  REVIEW,   ["INVALID_VALUE:age"]),
    (False, True,  True,  False, REVIEW,   ["INVALID_VALUE:age", "LOW_CONFIDENCE:monthly_income"]),
    (False, True,  True,  True,  REVIEW,   ["INVALID_VALUE:age", "LOW_CONFIDENCE:monthly_income"]),
    (True,  False, False, False, REVIEW,   FAILED),
    (True,  False, False, True,  REVIEW,   FAILED),
    (True,  False, True,  False, REVIEW,   FAILED),
    (True,  False, True,  True,  REVIEW,   FAILED),
    (True,  True,  False, False, REVIEW,   FAILED),
    (True,  True,  False, True,  REVIEW,   FAILED),
    (True,  True,  True,  False, REVIEW,   FAILED),
    (True,  True,  True,  True,  REVIEW,   FAILED),
]


def row_id(row) -> str:
    names = ("failed", "invalid", "low", "decline")
    on = [name for name, value in zip(names, row[:4]) if value]
    return "+".join(on) or "clean"


def test_truth_table_covers_every_combination_once():
    combos = [row[:4] for row in TRUTH_TABLE]

    assert len(combos) == 16
    assert set(combos) == set(product([False, True], repeat=4))


@pytest.mark.parametrize(
    "failed, invalid, low, decline, expected_decision, expected_codes",
    TRUTH_TABLE,
    ids=[row_id(row) for row in TRUTH_TABLE],
)
def test_precedence_truth_table(
    failed, invalid, low, decline, expected_decision, expected_codes
):
    result = route_decision(
        extraction_status=ExtractionStatus.TIMEOUT if failed else ExtractionStatus.OK,
        invalid_fields=("age",) if invalid else (),
        low_confidence_fields=("monthly_income",) if low else (),
        decline_flags=("FOIR_TOO_HIGH",) if decline else (),
    )

    assert result.decision == expected_decision
    assert result.reason_codes == expected_codes


def test_critical_fields_are_the_fields_the_rules_read():
    assert CRITICAL_FIELDS == (
        "age",
        "monthly_income",
        "existing_emis",
        "requested_amount",
        "tenure_months",
    )


# -----------------------------
# Row 1: extraction failures
# -----------------------------
FAILURE_CODES = [
    (ExtractionStatus.API_ERROR, "EXTRACTION_FAILED:api_error"),
    (ExtractionStatus.TIMEOUT, "EXTRACTION_FAILED:timeout"),
    (ExtractionStatus.REFUSED, "EXTRACTION_FAILED:refused"),
    (ExtractionStatus.TRUNCATED, "EXTRACTION_FAILED:truncated"),
    (ExtractionStatus.INVALID_OUTPUT, "EXTRACTION_FAILED:invalid_output"),
]


def test_failure_codes_cover_every_failed_status():
    failed_statuses = {s for s in ExtractionStatus if s != ExtractionStatus.OK}

    assert {status for status, _ in FAILURE_CODES} == failed_statuses


@pytest.mark.parametrize("status, expected_code", FAILURE_CODES)
def test_each_failed_status_has_its_own_code(status, expected_code):
    result = route_decision(extraction_status=status)

    assert result.decision == REVIEW
    assert result.reason_codes == [expected_code]


def test_failed_extraction_reason_names_the_status():
    result = route_decision(extraction_status=ExtractionStatus.TIMEOUT)

    assert result.reason == "Extraction failed (timeout); routed to human review."


# -----------------------------
# Rows 2 and 3: review causes
# -----------------------------
def test_missing_value_code_and_reason():
    result = route_decision(missing_fields=("age",))

    assert result.decision == REVIEW
    assert result.reason_codes == ["MISSING_VALUE:age"]
    assert result.reason == "Missing value for age; routed to human review."


def test_missing_codes_come_before_invalid_codes():
    result = route_decision(missing_fields=("tenure_months",), invalid_fields=("age",))

    assert result.reason_codes == ["MISSING_VALUE:tenure_months", "INVALID_VALUE:age"]
    assert result.reason == (
        "Missing value for tenure_months; Invalid value for age; "
        "routed to human review."
    )


def test_several_fields_keep_their_order():
    result = route_decision(invalid_fields=("age", "monthly_income"))

    assert result.reason_codes == ["INVALID_VALUE:age", "INVALID_VALUE:monthly_income"]
    assert result.reason == (
        "Invalid values for age, monthly_income; routed to human review."
    )


def test_low_confidence_reason_names_the_fields():
    result = route_decision(low_confidence_fields=("monthly_income", "tenure_months"))

    assert result.reason_codes == [
        "LOW_CONFIDENCE:monthly_income",
        "LOW_CONFIDENCE:tenure_months",
    ]
    assert result.reason == (
        "Low confidence for monthly_income, tenure_months; routed to human review."
    )


def test_invalid_field_is_not_also_reported_as_low_confidence():
    result = route_decision(
        invalid_fields=("age",),
        low_confidence_fields=("age", "monthly_income"),
    )

    assert result.reason_codes == ["INVALID_VALUE:age", "LOW_CONFIDENCE:monthly_income"]


def test_missing_field_is_not_also_reported_as_low_confidence():
    result = route_decision(
        missing_fields=("monthly_income",),
        low_confidence_fields=("monthly_income",),
    )

    assert result.reason_codes == ["MISSING_VALUE:monthly_income"]
    assert result.reason == "Missing value for monthly_income; routed to human review."


# -----------------------------
# Rows 4 and 5: decline and eligible
# -----------------------------
def test_decline_flags_keep_their_order_and_appear_in_reason():
    flags = ("FOIR_TOO_HIGH", "INCOME_BELOW_MINIMUM")

    result = route_decision(decline_flags=flags)

    assert result.decision == DECLINE
    assert result.reason_codes == ["FOIR_TOO_HIGH", "INCOME_BELOW_MINIMUM"]
    for flag in flags:
        assert flag in result.reason


def test_eligible_has_no_codes_and_a_reason():
    result = route_decision()

    assert result.decision == ELIGIBLE
    assert result.reason_codes == []
    assert result.reason != ""


def test_result_cannot_be_changed():
    result = route_decision()

    with pytest.raises(dataclasses.FrozenInstanceError):
        result.decision = DECLINE