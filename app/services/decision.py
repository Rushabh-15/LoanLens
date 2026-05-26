from app.models.schemas import DecisionType


DECLINE_FLAGS = {
    "FOIR_TOO_HIGH",
    "INCOME_BELOW_MINIMUM",
    "AMOUNT_DISPROPORTIONATE"
}

REVIEW_FLAGS = {
    "MISSING_CRITICAL_FIELD"
}


def route_decision(
    risk_flags: list[str],
    has_low_confidence: bool
) -> tuple[DecisionType, str]:
    """
    Return the final application decision
    and a human-readable reason.
    """

    if has_low_confidence:
        return (
            DecisionType.NEEDS_REVIEW,
            "Low-confidence extraction; routed to human review."
        )

    if any(
        flag in REVIEW_FLAGS
        for flag in risk_flags
    ):
        return (
            DecisionType.NEEDS_REVIEW,
            "Missing critical information; routed to human review."
        )

    decline_flags_found = [
        flag
        for flag in risk_flags
        if flag in DECLINE_FLAGS
    ]

    if decline_flags_found:
        return (
            DecisionType.DECLINE,
            (
                "Declined due to: "
                f"{', '.join(decline_flags_found)}"
            )
        )

    return (
        DecisionType.ELIGIBLE,
        "Passed all checks."
    )