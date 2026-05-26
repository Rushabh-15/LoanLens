from app.services.pdf_extractor import extract_text_from_pdf


with open(
    "sample_data/sample_application.pdf",
    "rb"
) as file:
    pdf_bytes = file.read()

text = extract_text_from_pdf(pdf_bytes)

print("Text length:", len(text))

print("\nFirst 200 characters:\n")

print(text[:200])