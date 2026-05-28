from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import Application

db = SessionLocal()

query = select(Application).where(
    Application.decision == "needs_review"
)

results = db.execute(query)

apps = results.scalars().all()

for app in apps:
    print(app.id, app.decision)

db.close()