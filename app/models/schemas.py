from enum import Enum

from pydantic import BaseModel, Field

class EmploymentType(str, Enum):
    self_employed = "self_employed"
    salaried = "salaried"

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

class DecisionType(str, Enum):
    ELIGIBLE = "eligible"
    DECLINE = "decline"
    NEEDS_REVIEW = "needs_review"

class RiskMetrics(BaseModel):
    estimated_emi: float
    foir: float
    risk_flags: list[str]

class DecisionResponse(BaseModel):
    decision: DecisionType
    reason: str

    applicant: ApplicantData
    metrics: RiskMetrics