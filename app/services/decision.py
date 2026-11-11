"""Decision router: turn the facts about one application into a decision.

Precedence, highest first:
    1. Extraction failed                    -> needs review
    2. A critical value is missing/invalid  -> needs review
    3. A critical field has low confidence  -> needs review
    4. Any decline flag                     -> decline
    5. Otherwise                            -> eligible
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.models.schemas import DecisionType, ExtractionStatus


# The only fields validation and the rules read. Their confidence decides
# routing; a low score on name, employer or purpose does not.
CRITICAL_FIELDS = (
    "age",
    "monthly_income",
    "existing_emis",
    "requested_amount",
    "tenure_months",
)

REVIEW_SUFFIX = "routed to human review."


@dataclass(frozen=True)
class RoutingResult:
    decision: DecisionType
    reason_codes: list[str]
    reason: str


def _describe(singular: str, plural: str, fields: Sequence[str]) -> str:
    """Return e.g. 'Missing value for age' or 'Missing values for age, tenure_months'."""
    label = singular if len(fields) == 1 else plural
    return f"{label} for {', '.join(fields)}"


def route_decision(
    *,
    extraction_status: ExtractionStatus = ExtractionStatus.OK,
    missing_fields: Sequence[str] = (),
    invalid_fields: Sequence[str] = (),
    low_confidence_fields: Sequence[str] = (),
    decline_flags: Sequence[str] = (),
) -> RoutingResult:
    """Apply the review precedence and return the decision, reason codes and text."""

    # Row 1: a failed extraction makes every other fact meaningless.
    if extraction_status != ExtractionStatus.OK:
        status = extraction_status.value  # .value: f"{enum}" gives the class name on 3.11+
        return RoutingResult(
            decision=DecisionType.NEEDS_REVIEW,
            reason_codes=[f"EXTRACTION_FAILED:{status}"],
            reason=f"Extraction failed ({status}); {REVIEW_SUFFIX}",
        )

    # Rows 2 and 3: list every review cause, one code per field.
    # A field that is missing or invalid is not also reported as low confidence.
    already_reported = set(missing_fields) | set(invalid_fields)
    low_only = [
        field for field in low_confidence_fields if field not in already_reported
    ]

    reason_codes = [
        *(f"MISSING_VALUE:{field}" for field in missing_fields),
        *(f"INVALID_VALUE:{field}" for field in invalid_fields),
        *(f"LOW_CONFIDENCE:{field}" for field in low_only),
    ]

    if reason_codes:
        messages = []
        if missing_fields:
            messages.append(_describe("Missing value", "Missing values", missing_fields))
        if invalid_fields:
            messages.append(_describe("Invalid value", "Invalid values", invalid_fields))
        if low_only:
            messages.append(_describe("Low confidence", "Low confidence", low_only))

        return RoutingResult(
            decision=DecisionType.NEEDS_REVIEW,
            reason_codes=reason_codes,
            reason="; ".join([*messages, REVIEW_SUFFIX]),
        )

    # Row 4: decline flags count only when no review condition is present.
    if decline_flags:
        return RoutingResult(
            decision=DecisionType.DECLINE,
            reason_codes=list(decline_flags),
            reason=f"Declined due to: {', '.join(decline_flags)}",
        )

    # Row 5.
    return RoutingResult(
        decision=DecisionType.ELIGIBLE,
        reason_codes=[],
        reason="Passed all checks.",
    )