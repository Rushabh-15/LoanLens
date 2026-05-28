import sys
from pathlib import Path

from app.services.confidence import has_low_confidence

from app.services.llm_extractor import extract_fields

from app.services.pdf_extractor import (
    extract_text_from_pdf,
    NoExtractableTextError,
)


PDF_PATH = Path("sample_data/sample_application.pdf")


def main():

    try:
        # -----------------------------
        # 1. Read PDF bytes
        # -----------------------------
        if not PDF_PATH.exists():
            print(f"ERROR: PDF not found at {PDF_PATH}")
            sys.exit(1)

        pdf_bytes = PDF_PATH.read_bytes()

        # -----------------------------
        # 2. Extract text from PDF
        # -----------------------------
        print("\n[STEP 1] Extracting text from PDF...\n")

        text = extract_text_from_pdf(pdf_bytes)

        print("Text extraction successful.")
        print(f"Length: {len(text)} characters\n")

        print("Preview:\n")
        print(text[:500])

        print("\n" + "-" * 60)

        # -----------------------------
        # 3. Run LLM extraction
        # -----------------------------
        print("\n[STEP 2] Sending text to Claude...\n")

        extracted = extract_fields(text)

        print("LLM extraction completed.\n")

        # -----------------------------
        # 4. Print structured output
        # -----------------------------
        print("[STRUCTURED OUTPUT]\n")

        print(extracted.model_dump())

        print("\n" + "-" * 60)

        # -----------------------------
        # 5. Confidence analysis
        # -----------------------------
        print("\n[STEP 3] Confidence analysis...\n")

        low_confidence = has_low_confidence(extracted)

        print(
            f"Has low-confidence fields: {low_confidence}"
        )

        print("\nPer-field confidence:\n")

        for field_name, field_value in extracted.__dict__.items():

            print(
                f"- {field_name}: "
                f"value={field_value.value} | "
                f"confidence={field_value.confidence}"
            )

        print("\nDONE ✔")

    # -----------------------------
    # PDF Extraction Failure
    # -----------------------------
    except NoExtractableTextError as e:

        print("\n[PDF ERROR]")
        print(str(e))

        sys.exit(1)

    # -----------------------------
    # Unexpected Failure
    # -----------------------------
    except Exception as e:

        print("\n[UNEXPECTED ERROR]")
        print(str(e))

        sys.exit(1)


if __name__ == "__main__":
    main()