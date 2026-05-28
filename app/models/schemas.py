from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# -------------------------
# Applicant Enums
# -------------------------
class EmploymentType(str, Enum):
    self_employed = "self_employed"
    salaried = "salaried"


class DecisionType(str, Enum):
    ELIGIBLE = "eligible"
    DECLINE = "decline"
    NEEDS_REVIEW = "needs_review"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


# -------------------------
# Strict Human Input Schema
# -------------------------
class ApplicantData(BaseModel):
    name: str
    age: int = Field(ge=18)

    employment_type: EmploymentType
    employer: str

    monthly_income: float = Field(gt=0)
    existing_emis: float = Field(ge=0)

    requested_amount: float = Field(gt=0)
    tenure_months: int = Field(gt=0)

    purpose: str


# -------------------------
# Decision Output Models
# -------------------------
class RiskMetrics(BaseModel):
    estimated_emi: float
    foir: float
    risk_flags: list[str]


class DecisionResponse(BaseModel):
    decision: DecisionType
    reason: str

    applicant: ApplicantData
    metrics: RiskMetrics


# -------------------------
# Typed Extraction Wrappers
# -------------------------
class StringField(BaseModel):
    value: Optional[str] = None
    confidence: Confidence


class IntField(BaseModel):
    value: Optional[int] = None
    confidence: Confidence


class FloatField(BaseModel):
    value: Optional[float] = None
    confidence: Confidence


# -------------------------
# LLM Extraction Schema
# -------------------------
class ExtractedFields(BaseModel):
    name: StringField
    age: IntField

    employment_type: StringField
    employer: StringField

    monthly_income: FloatField
    existing_emis: FloatField

    requested_amount: FloatField
    tenure_months: IntField

    purpose: StringField

    @classmethod
    def all_low(cls) -> "ExtractedFields":
        """
        Safe fallback object used when extraction fails.
        """

        return cls(
            name=StringField(
                value=None,
                confidence=Confidence.low
            ),
            age=IntField(
                value=None,
                confidence=Confidence.low
            ),
            employment_type=StringField(
                value=None,
                confidence=Confidence.low
            ),
            employer=StringField(
                value=None,
                confidence=Confidence.low
            ),
            monthly_income=FloatField(
                value=None,
                confidence=Confidence.low
            ),
            existing_emis=FloatField(
                value=None,
                confidence=Confidence.low
            ),
            requested_amount=FloatField(
                value=None,
                confidence=Confidence.low
            ),
            tenure_months=IntField(
                value=None,
                confidence=Confidence.low
            ),
            purpose=StringField(
                value=None,
                confidence=Confidence.low
            ),
        )