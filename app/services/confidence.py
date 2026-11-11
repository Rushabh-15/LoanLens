from app.models.schemas import Confidence, ExtractedFields
from app.services.decision import CRITICAL_FIELDS


def low_confidence_fields(fields: ExtractedFields) -> list[str]:
    """
    Return the critical fields the model labelled low confidence.

    Only CRITICAL_FIELDS count: a low score on name, employer, purpose or
    employment type does not affect the decision, so it does not send the
    case to review. MEDIUM is accepted until the C2 accuracy-by-confidence
    table shows otherwise.

    The result follows CRITICAL_FIELDS order, so reason codes are stable.
    """
    return [
        field_name
        for field_name in CRITICAL_FIELDS
        if getattr(fields, field_name).confidence == Confidence.low
    ]