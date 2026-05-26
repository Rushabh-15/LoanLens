import io

import pdfplumber


class NoExtractableTextError(Exception):
    """
    Raised when a PDF contains no extractable text.
    """


def extract_text_from_pdf(
    file_bytes: bytes
) -> str:
    """
    Extract and return text from PDF bytes.

    Raises NoExtractableTextError if the PDF
    contains no extractable text.
    """

    extracted_pages = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text is not None:
                extracted_pages.append(page_text)

    combined_text = "\n".join(extracted_pages)

    if combined_text.strip() == "":
        raise NoExtractableTextError(
            "PDF contains no extractable text"
        )

    return combined_text