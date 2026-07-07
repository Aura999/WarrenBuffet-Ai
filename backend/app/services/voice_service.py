import os
import re
import tempfile

from app.core.config import OPENAI_TRANSCRIPTION_MODEL, TTS_PROVIDER, validate_settings


def _clean_error(exc: Exception) -> str:
    message = str(exc) or "Voice processing failed."
    return re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", message)


def transcribe_audio_file(file_path: str) -> dict:
    try:
        validate_settings()

        from openai import OpenAI

        client = OpenAI()

        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=OPENAI_TRANSCRIPTION_MODEL,
                file=audio_file,
            )

        transcript = getattr(transcription, "text", "") or ""

        return {
            "success": True,
            "transcript": transcript.strip(),
        }
    except Exception as exc:
        return {
            "success": False,
            "error": _clean_error(exc),
        }


def prepare_tts_text(answer: str, max_chars: int = 1500) -> str:
    text = answer or ""
    text = re.sub(r"\[Document Source \d+\]", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[#*_`>|-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars].rsplit(" ", 1)[0].strip()
    return (
        f"{truncated}. Audio summary generated from the first part of the answer."
    )


def text_to_speech(text: str) -> dict:
    try:
        if TTS_PROVIDER.lower() != "gtts":
            return {
                "success": False,
                "error": f"Unsupported TTS provider: {TTS_PROVIDER}",
            }

        from gtts import gTTS

        tts_text = prepare_tts_text(text)

        if not tts_text:
            return {
                "success": False,
                "error": "No text was provided for text-to-speech.",
            }

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.close()

        gTTS(text=tts_text, lang="en").save(temp_file.name)

        return {
            "success": True,
            "audio_path": temp_file.name,
            "shortened": len(tts_text) < len(re.sub(r"\s+", " ", text or "").strip()),
        }
    except Exception as exc:
        if "temp_file" in locals() and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

        return {
            "success": False,
            "error": _clean_error(exc),
        }
