from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

# Base class for all ORM models

class Base(DeclarativeBase):
    pass

# Database engine
engine = create_engine(get_settings().database_url)

# Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

# FastAPI dependency
def get_session():
    session = SessionLocal()

    try:
        yield session

    finally:
        session.close()

# Initialize database tables
def init_db():
    Base.metadata.create_all(bind=engine)