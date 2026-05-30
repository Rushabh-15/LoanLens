import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.services.llm_extractor import extract_fields


SAMPLES_DIR = Path(__file__).parent / "samples"
EXPECTED_DIR = Path(__file__).parent / "expected"

FIELDS = [
    "name",
    "age",
    "employment_type",
    "employer",
    "monthly_income",
    "existing_emis",
    "requested_amount",
    "tenure_months",
    "purpose",
]


def normalize(value):
    if isinstance(value, str):
        return value.strip().lower()
    return value


def get_extracted_value(extracted_fields, field_name):
    field = getattr(extracted_fields, field_name)
    return field.value


def run_eval():
    totals = {field: 0 for field in FIELDS}
    correct = {field: 0 for field in FIELDS}

    sample_files = sorted(SAMPLES_DIR.glob("*.txt"))

    if not sample_files:
        print("No eval samples found.")
        return

    for sample_path in sample_files:
        expected_path = EXPECTED_DIR / f"{sample_path.stem}.json"

        if not expected_path.exists():
            print(f"Missing expected file for {sample_path.name}")
            continue

        text = sample_path.read_text(encoding="utf-8")
        expected = json.loads(expected_path.read_text(encoding="utf-8"))

        extracted = extract_fields(text)

        print(f"\nSample: {sample_path.name}")

        for field in FIELDS:
            expected_value = expected.get(field)
            actual_value = get_extracted_value(extracted, field)

            is_correct = normalize(actual_value) == normalize(expected_value)

            totals[field] += 1
            correct[field] += int(is_correct)

            status = "PASS" if is_correct else "FAIL"
            print(
                f"  {field}: {status} "
                f"(expected={expected_value!r}, actual={actual_value!r})"
            )

    print("\nSummary")
    print("-" * 40)

    total_correct = 0
    total_count = 0

    for field in FIELDS:
        total_correct += correct[field]
        total_count += totals[field]
        print(f"{field}: {correct[field]}/{totals[field]} correct")

    accuracy = (total_correct / total_count) * 100 if total_count else 0
    print("-" * 40)
    print(f"Overall: {total_correct}/{total_count} correct ({accuracy:.1f}%)")


if __name__ == "__main__":
    run_eval()