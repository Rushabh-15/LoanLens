from app.models.schemas import (
    ExtractedFields,
    Confidence,
)


def has_low_confidence(
    fields: ExtractedFields
) -> bool:
    """
    Returns True if ANY field has low confidence.

    Design choice:
    - Only LOW confidence triggers review
    - MEDIUM confidence is treated as acceptable

    This can be tightened later if
    false-acceptance cost increases.
    """

    return any(
        getattr(fields, field_name).confidence == Confidence.low
        for field_name in ExtractedFields.model_fields
    )