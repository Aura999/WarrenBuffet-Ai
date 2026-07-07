from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi

from app.api.documents import router as documents_router
from app.api.voice import router as voice_router
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import handle_chat_request


app = FastAPI(
    title="WarrenBuffet.Ai API",
    version="0.1.0",
    openapi_version="3.0.3",
)

app.include_router(documents_router)
app.include_router(voice_router)


def custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    upload_schema = openapi_schema.get("components", {}).get("schemas", {}).get(
        "Body_upload_documents_api_documents_upload_post"
    )

    if upload_schema:
        files_schema = upload_schema.get("properties", {}).get("files")

        if files_schema and files_schema.get("type") == "array":
            files_schema["items"] = {
                "type": "string",
                "format": "binary",
            }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "WarrenBuffet.Ai backend is running."}


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = handle_chat_request(
            query=request.query,
            ticker=request.ticker,
            document_ids=request.document_ids,
        )
        return ChatResponse(
            success=result["success"],
            query=result["query"],
            answer=result["answer"],
            sources=result["sources"],
            visuals=result.get("visuals"),
        )
    except ValueError as exc:
        if "OPENAI_API_KEY is missing" in str(exc):
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        raise HTTPException(status_code=500, detail="Invalid chat request.") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate financial response: {exc}",
        ) from exc
