import json
import os
import tempfile
from typing import Optional

from starlette.background import BackgroundTask
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.chat_service import handle_chat_request
from app.services.voice_service import text_to_speech, transcribe_audio_file


router = APIRouter(prefix="/api/voice", tags=["voice"])

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg"}


class TTSRequest(BaseModel):
    text: str


def _is_supported_audio(file: UploadFile) -> bool:
    filename = file.filename or ""
    suffix = os.path.splitext(filename)[1].lower()
    return suffix in ALLOWED_AUDIO_EXTENSIONS


def _parse_document_ids(value: Optional[str]) -> list[str] | None:
    if not value:
        return None

    try:
        parsed = json.loads(value)

        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


async def _save_upload_to_temp(file: UploadFile) -> str:
    suffix = os.path.splitext(file.filename or "")[1].lower() or ".audio"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        return temp_file.name


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict:
    if not _is_supported_audio(file):
        return {
            "success": False,
            "error": "Unsupported audio format. Use mp3, wav, m4a, webm, or ogg.",
        }

    temp_path = None

    try:
        temp_path = await _save_upload_to_temp(file)
        return transcribe_audio_file(temp_path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/tts")
def create_tts_audio(request: TTSRequest):
    result = text_to_speech(request.text)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error") or "TTS failed.")

    audio_path = result["audio_path"]

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename="assistant_answer.mp3",
        background=BackgroundTask(os.unlink, audio_path),
    )


@router.post("/chat")
async def voice_chat(
    file: UploadFile = File(...),
    ticker: Optional[str] = Form(default=None),
    document_ids: Optional[str] = Form(default=None),
    include_audio: bool = Form(default=True),
) -> dict:
    if not _is_supported_audio(file):
        return {
            "success": False,
            "error": "Unsupported audio format. Use mp3, wav, m4a, webm, or ogg.",
        }

    temp_path = None

    try:
        temp_path = await _save_upload_to_temp(file)
        transcription = transcribe_audio_file(temp_path)

        if not transcription.get("success"):
            return transcription

        transcript = transcription.get("transcript", "").strip()

        if not transcript:
            return {
                "success": False,
                "error": "Could not detect speech. Try a clearer audio file.",
            }

        chat_result = handle_chat_request(
            query=transcript,
            ticker=ticker or None,
            document_ids=_parse_document_ids(document_ids),
        )

        return {
            "success": chat_result.get("success", True),
            "transcript": transcript,
            "answer": chat_result.get("answer", ""),
            "sources": chat_result.get("sources", []),
            "audio_available": bool(include_audio),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc) or "Voice chat failed.",
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
