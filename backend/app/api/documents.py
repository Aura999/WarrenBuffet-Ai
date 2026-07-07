import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.document_store import (
    create_document_id,
    delete_document,
    get_document_chunk,
    get_document_metadata,
    list_documents,
)
from app.services.pdf_loader import chunk_pdf_pages, extract_pdf_text
from app.services.rag_service import index_document


router = APIRouter(prefix="/api/documents", tags=["documents"])


def _is_pdf(file: UploadFile) -> bool:
    filename = file.filename or ""
    content_type = file.content_type or ""
    return filename.lower().endswith(".pdf") or content_type == "application/pdf"


@router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)) -> dict:
    documents = []

    for file in files:
        filename = file.filename or "uploaded.pdf"
        temp_path = None

        if not _is_pdf(file):
            documents.append(
                {
                    "filename": filename,
                    "status": "error",
                    "error": "Only PDF files are supported.",
                }
            )
            continue

        try:
            suffix = os.path.splitext(filename)[1] or ".pdf"

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_path = temp_file.name
                temp_file.write(await file.read())

            extraction = extract_pdf_text(temp_path)

            if not extraction.get("success"):
                documents.append(
                    {
                        "filename": filename,
                        "status": "error",
                        "error": extraction.get("error") or "PDF extraction failed.",
                    }
                )
                continue

            chunks = chunk_pdf_pages(extraction["pages"])

            if not chunks:
                documents.append(
                    {
                        "filename": filename,
                        "status": "error",
                        "error": "No text chunks could be created from the PDF.",
                    }
                )
                continue

            document_id = create_document_id()
            indexed = index_document(
                document_id=document_id,
                filename=filename,
                pages=extraction["pages"],
                chunks=chunks,
            )

            if not indexed.get("success"):
                documents.append(
                    {
                        "filename": filename,
                        "status": "error",
                        "error": indexed.get("error") or "Document indexing failed.",
                    }
                )
                continue

            documents.append(
                {
                    "document_id": document_id,
                    "filename": filename,
                    "page_count": extraction["page_count"],
                    "character_count": extraction["character_count"],
                    "chunk_count": len(chunks),
                    "status": "indexed",
                }
            )
        except Exception as exc:
            documents.append(
                {
                    "filename": filename,
                    "status": "error",
                    "error": str(exc) or "Document upload failed.",
                }
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

    return {
        "success": any(document.get("status") == "indexed" for document in documents),
        "documents": documents,
    }


@router.get("")
def get_documents() -> dict:
    return {
        "success": True,
        "documents": list_documents(),
    }


@router.get("/{document_id}")
def get_document(document_id: str) -> dict:
    metadata = get_document_metadata(document_id)

    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "success": True,
        "document": metadata,
    }


@router.get("/{document_id}/chunks/{chunk_index}")
def get_chunk(document_id: str, chunk_index: int) -> dict:
    chunk = get_document_chunk(document_id, chunk_index)

    if not chunk:
        raise HTTPException(status_code=404, detail="Document chunk not found.")

    return {
        "success": True,
        **chunk,
    }


@router.delete("/{document_id}")
def remove_document(document_id: str) -> dict:
    deleted = delete_document(document_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "success": True,
        "document_id": document_id,
        "status": "deleted",
    }
