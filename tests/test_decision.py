import pytest

from app.models.schemas import DecisionType

from app.services.decision import route_decision


@pytest.mark.parametrize(
    (
        "has_low_confidence",
        "risk_flags",
        "expected_decision"
    ),
    [
        (
            False,
            [],
            DecisionType.ELIGIBLE
        ),
        (
            False,
            ["FOIR_TOO_HIGH"],
            DecisionType.DECLINE
        ),
        (
            False,
            ["INCOME_BELOW_MINIMUM"],
            DecisionType.DECLINE
        ),
        (
            False,
            ["AMOUNT_DISPROPORTIONATE"],
            DecisionType.DECLINE
        ),
        (
            False,
            ["MISSING_CRITICAL_FIELD"],
            DecisionType.NEEDS_REVIEW
        ),
        (
            False,
            [
                "FOIR_TOO_HIGH",
                "INCOME_BELOW_MINIMUM"
            ],
            DecisionType.DECLINE
        ),
        (
            True,
            [],
            DecisionType.NEEDS_REVIEW
        ),
        (
            True,
            ["FOIR_TOO_HIGH"],
            DecisionType.NEEDS_REVIEW
        ),
        (
            True,
            ["MISSING_CRITICAL_FIELD"],
            DecisionType.NEEDS_REVIEW
        ),
    ]
)
def test_route_decision_truth_table(
    has_low_confidence,
    risk_flags,
    expected_decision
):
    decision, reason = route_decision(
        risk_flags=risk_flags,
        has_low_confidence=has_low_confidence
    )

    assert decision == expected_decision


def test_eligible_reason_is_not_empty():
    decision, reason = route_decision(
        risk_flags=[],
        has_low_confidence=False
    )

    assert reason != ""


def test_decline_reason_is_not_empty():
    decision, reason = route_decision(
        risk_flags=["FOIR_TOO_HIGH"],
        has_low_confidence=False
    )

    assert reason != ""


def test_review_reason_is_not_empty():
    decision, reason = route_decision(
        risk_flags=[],
        has_low_confidence=True
    )

    assert reason != ""

def test_decline_reason_contains_triggering_flag():
    decision, reason = route_decision(
        risk_flags=["FOIR_TOO_HIGH"],
        has_low_confidence=False
    )

    assert "FOIR_TOO_HIGH" in reason