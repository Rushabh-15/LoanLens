from sqlalchemy import select

from app.db import SessionLocal
from app.models.db_models import Application


def main():
    db = SessionLocal()

    try:
        query = select(Application).where(
            Application.status == "needs_review"
        )

        results = db.execute(query)

        applications = results.scalars().all()

        print(f"\nFound {len(applications)} applications:\n")

        for app in applications:
            print(
                f"ID={app.id} | "
                f"Decision={app.decision} | "
                f"Status={app.status}"
            )

    finally:
        db.close()


if __name__ == "__main__":
    main()