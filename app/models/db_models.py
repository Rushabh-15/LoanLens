from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Extracted structured fields + confidence
    extracted_fields: Mapped[dict] = mapped_column(JSON)

    # Financial calculations
    emi: Mapped[float] = mapped_column(Float)

    foir: Mapped[float] = mapped_column(Float)

    # Risk analysis
    risk_flags: Mapped[list[str]] = mapped_column(JSON)

    # Final decisioning
    decision: Mapped[str] = mapped_column(String)

    reason: Mapped[str] = mapped_column(String)

    # Review queue workflow
    status: Mapped[str] = mapped_column(
        String,
        default="pending_review"
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )