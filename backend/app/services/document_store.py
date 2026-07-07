from uuid import uuid4


DOCUMENT_REGISTRY = {}
VECTOR_STORES = {}


def create_document_id() -> str:
    return f"doc_{uuid4().hex}"


def add_document(
    document_id: str,
    metadata: dict,
    chunks: list,
    vector_store,
) -> None:
    DOCUMENT_REGISTRY[document_id] = {
        **metadata,
        "document_id": document_id,
        "chunks": chunks,
    }
    VECTOR_STORES[document_id] = vector_store


def get_document_metadata(document_id: str) -> dict | None:
    document = DOCUMENT_REGISTRY.get(document_id)

    if not document:
        return None

    return {
        key: value
        for key, value in document.items()
        if key != "chunks"
    }


def get_document_chunk(document_id: str, chunk_index: int) -> dict | None:
    document = DOCUMENT_REGISTRY.get(document_id)

    if not document:
        return None

    for chunk in document.get("chunks", []):
        if chunk.get("chunk_index") == chunk_index:
            return {
                "document_id": document_id,
                "filename": document.get("filename"),
                **chunk,
            }

    return None


def list_documents() -> list:
    return [
        get_document_metadata(document_id)
        for document_id in DOCUMENT_REGISTRY
    ]


def get_vector_store(document_id: str):
    return VECTOR_STORES.get(document_id)


def delete_document(document_id: str) -> bool:
    existed = document_id in DOCUMENT_REGISTRY

    DOCUMENT_REGISTRY.pop(document_id, None)
    VECTOR_STORES.pop(document_id, None)

    return existed
