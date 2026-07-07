import numpy as np
from langchain_openai import OpenAIEmbeddings

from app.core.config import OPENAI_EMBEDDING_MODEL, validate_settings
from app.services.document_store import (
    add_document,
    get_document_metadata,
    get_vector_store,
    list_documents,
)


def _embedder() -> OpenAIEmbeddings:
    validate_settings()
    return OpenAIEmbeddings(
        model=OPENAI_EMBEDDING_MODEL,
        tiktoken_enabled=False,
        check_embedding_ctx_length=False,
    )


def index_document(
    document_id: str,
    filename: str,
    pages: list,
    chunks: list,
) -> dict:
    try:
        import faiss

        if not chunks:
            return {
                "success": False,
                "error": "No text chunks were available for indexing.",
            }

        texts = [chunk["text"] for chunk in chunks]
        vectors = np.array(_embedder().embed_documents(texts), dtype="float32")

        if vectors.size == 0:
            return {
                "success": False,
                "error": "Embedding generation returned no vectors.",
            }

        index = faiss.IndexFlatL2(vectors.shape[1])
        index.add(vectors)

        vector_store = {
            "index": index,
            "chunks": [
                {
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": chunk["page_number"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                }
                for chunk in chunks
            ],
        }
        character_count = sum(len(page.get("text", "")) for page in pages)
        metadata = {
            "document_id": document_id,
            "filename": filename,
            "page_count": len(pages),
            "character_count": character_count,
            "chunk_count": len(chunks),
        }

        add_document(
            document_id=document_id,
            metadata=metadata,
            chunks=chunks,
            vector_store=vector_store,
        )

        return {
            "success": True,
            "document_id": document_id,
            "filename": filename,
            "chunk_count": len(chunks),
        }
    except Exception as exc:
        return {
            "success": False,
            "document_id": document_id,
            "filename": filename,
            "error": str(exc) or "Document indexing failed.",
        }


def retrieve_relevant_chunks(
    query: str,
    document_ids: list[str] | None = None,
    k: int = 5,
) -> dict:
    try:
        documents = list_documents()

        if not documents:
            return {
                "success": False,
                "error": "No documents have been uploaded or indexed.",
                "chunks": [],
            }

        selected_document_ids = document_ids or [
            document["document_id"]
            for document in documents
        ]
        query_vector = np.array([_embedder().embed_query(query)], dtype="float32")
        results = []
        seen = set()

        for document_id in selected_document_ids:
            metadata = get_document_metadata(document_id)
            vector_store = get_vector_store(document_id)

            if not metadata or not vector_store:
                results.append(
                    {
                        "document_id": document_id,
                        "error": "Document was not found or is not indexed.",
                    }
                )
                continue

            index = vector_store["index"]
            chunks = vector_store["chunks"]
            limit = min(k, len(chunks))

            if limit == 0:
                continue

            distances, indices = index.search(query_vector, limit)

            for distance, chunk_position in zip(distances[0], indices[0]):
                if chunk_position < 0:
                    continue

                chunk = chunks[int(chunk_position)]
                dedupe_key = (chunk["document_id"], chunk["chunk_index"])

                if dedupe_key in seen:
                    continue

                seen.add(dedupe_key)
                results.append(
                    {
                        **chunk,
                        "score": float(distance),
                    }
                )

        valid_results = [result for result in results if "text" in result]
        invalid_results = [result for result in results if "error" in result]

        valid_results.sort(key=lambda item: item["score"])

        if not valid_results:
            error = (
                invalid_results[0]["error"]
                if invalid_results
                else "No relevant document chunks were retrieved."
            )
            return {
                "success": False,
                "error": error,
                "chunks": [],
            }

        return {
            "success": True,
            "query": query,
            "chunks": valid_results[:k],
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc) or "Document retrieval failed.",
            "chunks": [],
        }
