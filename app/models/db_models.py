from datetime import datetime

from sqlalchemy import DateTime, Float, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.schemas import StatusType


class Application(Base):
    __tablename__ = "applications"

    # -------------------------
    # Primary Key
    # -------------------------
    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    # -------------------------
    # Extracted Data
    # -------------------------
    extracted_fields: Mapped[dict] = mapped_column(
        JSON
    )

    # -------------------------
    # Financial Metrics
    # -------------------------
    emi: Mapped[float] = mapped_column(
        Float
    )

    foir: Mapped[float] = mapped_column(
        Float
    )

    # -------------------------
    # Risk Evaluation
    # -------------------------
    risk_flags: Mapped[list[str]] = mapped_column(
        JSON
    )

    # -------------------------
    # Decision
    # -------------------------
    decision: Mapped[str] = mapped_column(
        String
    )

    reason: Mapped[str] = mapped_column(
        String
    )

    # -------------------------
    # Review Workflow
    # -------------------------
    status: Mapped[str] = mapped_column(
        String,
        default=StatusType.NEEDS_REVIEW.value,
    )

    # -------------------------
    # Audit Timestamp
    # -------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )