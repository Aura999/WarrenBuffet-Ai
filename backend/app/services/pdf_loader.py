import re


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_pdf_text(file_path: str) -> dict:
    try:
        import fitz

        pages = []
        character_count = 0

        with fitz.open(file_path) as document:
            page_count = document.page_count

            for index, page in enumerate(document, start=1):
                text = _normalize_whitespace(page.get_text("text"))

                if not text:
                    continue

                pages.append(
                    {
                        "page_number": index,
                        "text": text,
                    }
                )
                character_count += len(text)

        if not pages:
            return {
                "success": False,
                "error": "No extractable text found in PDF.",
                "pages": [],
                "page_count": 0,
                "character_count": 0,
            }

        return {
            "success": True,
            "pages": pages,
            "page_count": page_count,
            "character_count": character_count,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc) or "PDF text extraction failed.",
            "pages": [],
            "page_count": 0,
            "character_count": 0,
        }


def chunk_pdf_pages(
    pages: list,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list:
    chunks = []
    chunk_index = 0
    step = max(chunk_size - overlap, 1)

    for page in pages:
        text = _normalize_whitespace(page.get("text", ""))

        if not text:
            continue

        for start in range(0, len(text), step):
            chunk_text = text[start : start + chunk_size].strip()

            if not chunk_text:
                continue

            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "page_number": page["page_number"],
                    "text": chunk_text,
                }
            )
            chunk_index += 1

            if start + chunk_size >= len(text):
                break

    return chunks
