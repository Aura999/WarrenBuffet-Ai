import os

from dotenv import load_dotenv


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_TRANSCRIPTION_MODEL = os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "gtts")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "WarrenBuffet-Ai")


def _configure_langsmith_environment() -> None:
    if not LANGSMITH_TRACING or not LANGSMITH_API_KEY:
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_TRACING_V2"] = "true"
    os.environ.setdefault("LANGSMITH_API_KEY", LANGSMITH_API_KEY)
    os.environ.setdefault("LANGSMITH_PROJECT", LANGSMITH_PROJECT)
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ.setdefault("LANGCHAIN_API_KEY", LANGSMITH_API_KEY)
    os.environ.setdefault("LANGCHAIN_PROJECT", LANGSMITH_PROJECT)


_configure_langsmith_environment()

LANGSMITH_ENABLED = LANGSMITH_TRACING and bool(LANGSMITH_API_KEY)


def validate_settings() -> None:
    """Validate settings required only when LLM-backed features are used."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing. Add it to backend/.env")


def validate_tavily_settings() -> None:
    """Validate settings required only when news retrieval is used."""
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY is missing. Add it to backend/.env")
