from app.db import init_db, SessionLocal
from app.models.db_models import Application


def main():
    # Step 1: Create tables (safe to run multiple times)
    init_db()

    # Step 2: Open DB session
    session = SessionLocal()

    try:
        # Step 3: Create a dummy application row
        app = Application(
            extracted_fields={
                "name": {
                    "value": "John Doe",
                    "confidence": 0.97
                },
                "income": {
                    "value": 75000,
                    "confidence": 0.93
                }
            },
            emi=14500.75,
            foir=0.38,
            risk_flags=["low_risk", "stable_income"],
            decision="eligible",
            reason="Strong income and low FOIR",
            status="completed"
        )

        # Step 4: Insert into DB
        session.add(app)
        session.commit()

        # ID should now be generated
        print(f"\nInserted row with ID: {app.id}")

        # Step 5: Fetch it back using primary key lookup
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