from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    applicant_name: Mapped[str]
    loan_amount: Mapped[float]
    