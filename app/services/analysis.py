from dataclasses import dataclass
from decimal import Decimal

from app.models.schemas import DecisionType
from app.services.decision import route_decision
from app.services.rules_engine import (
    DEFAULT_POLICY,
    LendingPolicy,
    calculate_emi,
    calculate_foir,
    evaluate_risk_flags,
)


@dataclass
class AnalysisResult:
    emi: Decimal
    foir: Decimal
    risk_flags: list[str]
    decision: DecisionType
    reason: str


def validate_inputs(applicant_data: dict) -> tuple[list[str], list[str]]:
    """Return risk flags and messages identifying the failing fields."""
    critical_fields = (
        "age",
        "monthly_income",
        "existing_emis",
        "requested_amount",
        "tenure_months",
    )

    missing_fields = [
        field_name
        for field_name in critical_fields
        if applicant_data.get(field_name) is None
    ]

    age = applicant_data.get("age")
    monthly_income = applicant_data.get("monthly_income")
    existing_emis = applicant_data.get("existing_emis")
    requested_amount = applicant_data.get("requested_amount")
    tenure_months = applicant_data.get("tenure_months")

    invalid_fields = []

    if age is not None and age < 18:
        invalid_fields.append("age")

    if monthly_income is not None and monthly_income <= 0:
        invalid_fields.append("monthly_income")

    if existing_emis is not None and existing_emis < 0:
        invalid_fields.append("existing_emis")

    if requested_amount is not None and requested_amount <= 0:
        invalid_fields.append("requested_amount")

    if tenure_months is not None and tenure_months <= 0:
        invalid_fields.append("tenure_months")

    risk_flags = []
    validation_messages = []

    if missing_fields:
        risk_flags.append("MISSING_CRITICAL_FIELD")
        label = "value" if len(missing_fields) == 1 else "values"
        validation_messages.append(
            f"Missing {label} for {', '.join(missing_fields)}"
        )

    if invalid_fields:
        risk_flags.append("INVALID_VALUE")
        label = "value" if len(invalid_fields) == 1 else "values"
        validation_messages.append(
            f"Invalid {label} for {', '.join(invalid_fields)}"
        )

    return risk_flags, validation_messages

def to_decimal(value: int | float | Decimal) -> Decimal:
    """Convert an input number to Decimal through str, so 0.1 stays exactly 0.1."""
    return Decimal(str(value))



def analyze_applicant(
    applicant_data: dict,
    has_low_confidence: bool = False,
    policy: LendingPolicy = DEFAULT_POLICY,
) -> AnalysisResult:
    """Validate inputs, calculate metrics, and route the decision."""

    # Validate before performing any financial calculations.
    risk_flags, validation_messages = validate_inputs(applicant_data)

    if risk_flags:
        decision, _ = route_decision(
            risk_flags=risk_flags,
            has_low_confidence=has_low_confidence,
        )

        # Preserve field names even when confidence is also low.
        if has_low_confidence:
            validation_messages.append("low-confidence extraction")

        reason = "; ".join(
            [*validation_messages, "routed to human review."]
        )

        # Calculations were skipped; retain the existing placeholders.
        return AnalysisResult(
            emi=Decimal("0"),
            foir=Decimal("0"),
            risk_flags=risk_flags,
            decision=decision,
            reason=reason,
        )

    # Valid inputs continue through the normal calculation path.
    # Convert at the boundary: the rules engine accepts only Decimal.
    monthly_income = to_decimal(applicant_data["monthly_income"])
    existing_emis = to_decimal(applicant_data["existing_emis"])
    requested_amount = to_decimal(applicant_data["requested_amount"])
    tenure_months = applicant_data["tenure_months"]

    emi = calculate_emi(
        principal=requested_amount,
        annual_rate=policy.default_annual_rate,
        tenure_months=tenure_months,
    )

    foir = calculate_foir(
        existing_emis=existing_emis,
        new_emi=emi,
        monthly_income=monthly_income,
    )

    risk_flags = evaluate_risk_flags(
        foir=foir,
        monthly_income=monthly_income,
        requested_amount=requested_amount,
        policy=policy,
    )

    decision, reason = route_decision(
        risk_flags=risk_flags,
        has_low_confidence=has_low_confidence,
    )

    return AnalysisResult(
        emi=emi,
        foir=foir,
        risk_flags=risk_flags,
        decision=decision,
        reason=reason,
    )
