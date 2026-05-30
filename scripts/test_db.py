from app.db import init_db, SessionLocal
from app.models.db_models import Application
from app.models.schemas import StatusType


def main():
    # Step 1: Create tables
    init_db()

    # Step 2: Open DB session
    session = SessionLocal()

    try:
        # Step 3: Create dummy application
        app = Application(
            extracted_fields={
                "name": {
                    "value": "John Doe",
                    "confidence": "high"
                },
                "monthly_income": {
                    "value": 75000,
                    "confidence": "high"
                }
            },
            emi=14500.75,
            foir=0.38,
            risk_flags=[],
            decision="eligible",
            reason="Passed all checks.",
            status=StatusType.PROCESSED.value
        )

        # Step 4: Insert into DB
        session.add(app)
        session.commit()

        print(f"\nInserted row with ID: {app.id}")

        # Step 5: Fetch row back
        fetched = session.get(Application, app.id)

        print("\nFetched from DB:")
        print("ID:", fetched.id)
        print("Decision:", fetched.decision)
        print("EMI:", fetched.emi)
        print("FOIR:", fetched.foir)
        print("Risk Flags:", fetched.risk_flags)
        print("Extracted Fields:", fetched.extracted_fields)
        print("Status:", fetched.status)
        print("Created At:", fetched.created_at)

        print("\n✅ DB isolation test PASSED")

    except Exception as e:
        session.rollback()

        print("\n❌ DB isolation test FAILED")
        print("Error:", str(e))

    finally:
        session.close()


if __name__ == "__main__":
    main()