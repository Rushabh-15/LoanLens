from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.models.schemas import DecisionType, ExtractionStatus
from app.services.decision import CRITICAL_FIELDS, route_decision
from app.services.rules_engine import (
    DEFAULT_POLICY,
    LendingPolicy,
    calculate_emi,
    calculate_foir,
    evaluate_risk_flags,
)


ZERO = Decimal("0")

# One rule per critical field: True means the value can be used.
# Missing values (None) are reported separately and never reach these rules.
FIELD_RULES: dict[str, Callable[[int | float], bool]] = {
    "age": lambda value: value >= 18,
    "monthly_income": lambda value: value > 0,
    "existing_emis": lambda value: value >= 0,
    "requested_amount": lambda value: value > 0,
    "tenure_months": lambda value: value > 0,
}


@dataclass
class AnalysisResult:
    emi: Decimal
    foir: Decimal
    risk_flags: list[str]
    decision: DecisionType
    reason: str
    reason_codes: list[str]


def validate_inputs(applicant_data: dict) -> tuple[list[str], list[str]]:
    """
    Return (missing_fields, invalid_fields), each in CRITICAL_FIELDS order.

    This function only finds problems. Wording and routing belong to
    decision.route_decision().
    """
    missing_fields = [
        field_name
        for field_name in CRITICAL_FIELDS
        if applicant_data.get(field_name) is None
    ]

    invalid_fields = [
        field_name
        for field_name in CRITICAL_FIELDS
        if applicant_data.get(field_name) is not None
        and not FIELD_RULES[field_name](applicant_data[field_name])
    ]

    return missing_fields, invalid_fields


def to_decimal(value: int | float | Decimal) -> Decimal:
    """Convert an input number to Decimal through str, so 0.1 stays exactly 0.1."""
    return Decimal(str(value))


def _calculate(
    applicant_data: dict,
    policy: LendingPolicy,
) -> tuple[Decimal, Decimal, list[str]]:
    """Return EMI, FOIR and decline flags. Inputs must already be valid."""
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

    decline_flags = evaluate_risk_flags(
        foir=foir,
        monthly_income=monthly_income,
        requested_amount=requested_amount,
        policy=policy,
    )

    return emi, foir, decline_flags


def analyze_applicant(
    applicant_data: dict,
    *,
    low_confidence_fields: Sequence[str] = (),
    extraction_status: ExtractionStatus = ExtractionStatus.OK,
    policy: LendingPolicy = DEFAULT_POLICY,
) -> AnalysisResult:
    """
    Collect the facts about one application, then let the router decide once.

    1. A failed extraction skips validation and calculation.
    2. Missing or invalid critical values skip calculation.
    3. Otherwise EMI, FOIR and decline flags are calculated, even when a
       critical field has low confidence, so the reviewer sees the numbers.
    """
    extraction_ok = extraction_status == ExtractionStatus.OK

    if extraction_ok:
        missing_fields, invalid_fields = validate_inputs(applicant_data)
    else:
        missing_fields, invalid_fields = [], []

    emi, foir, decline_flags = ZERO, ZERO, []

    if extraction_ok and not missing_fields and not invalid_fields:
        emi, foir, decline_flags = _calculate(applicant_data, policy)

    routed = route_decision(
        extraction_status=extraction_status,
        missing_fields=missing_fields,
        invalid_fields=invalid_fields,
        low_confidence_fields=low_confidence_fields,
        decline_flags=decline_flags,
    )

    # risk_flags keeps its existing meaning for the API: what the checks found.
    # reason_codes (from the router) say why the case got its decision.
    risk_flags = [
        *(["MISSING_CRITICAL_FIELD"] if missing_fields else []),
        *(["INVALID_VALUE"] if invalid_fields else []),
        *decline_flags,
    ]

    return AnalysisResult(
        emi=emi,
        foir=foir,
        risk_flags=risk_flags,
        decision=routed.decision,
        reason=routed.reason,
        reason_codes=routed.reason_codes,
    )