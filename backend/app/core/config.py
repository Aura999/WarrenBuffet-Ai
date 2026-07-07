import os

from dotenv import load_dotenv


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "gtts")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def validate_settings() -> None:
    """Validate settings required only when LLM-backed features are used."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing. Add it to backend/.env")


def validate_tavily_settings() -> None:
    """Validate settings required only when news retrieval is used."""
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY is missing. Add it to backend/.env")
