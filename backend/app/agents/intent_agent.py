import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import OPENAI_MODEL, validate_settings


VALID_INTENTS = {
    "casual_chat",
    "identity_question",
    "capability_question",
    "clarification_or_planning",
    "financial_analysis",
    "document_query",
    "voice_meta",
}


def _normalized(query: str) -> str:
    return re.sub(r"\s+", " ", (query or "").strip().lower())


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _is_short_casual(text: str) -> bool:
    casual_exact = {
        "hi",
        "hii",
        "hello",
        "hey",
        "hi bro",
        "hii bro",
        "hello bro",
        "hey bro",
        "thanks",
        "thank you",
        "thank u",
        "ok thanks",
    }
    casual_phrases = (
        "how are you",
        "what's up",
        "whats up",
        "good morning",
        "good afternoon",
        "good evening",
    )
    return text in casual_exact or (
        len(text.split()) <= 8 and _has_any(text, casual_phrases)
    )


def _deterministic_intent(
    query: str,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
) -> str | None:
    text = _normalized(query)

    if not text:
        return "clarification_or_planning"

    identity_terms = (
        "who are you",
        "who are u",
        "what are you",
        "are you chatgpt",
        "are you openai",
        "are you gpt",
        "what model are you",
        "which model are you",
        "who built you",
        "who made you",
        "your creator",
        "created you",
    )
    capability_terms = (
        "what can you do",
        "how can you help",
        "your features",
        "what are your features",
        "can you analyze stocks",
        "can you analyse stocks",
        "can you read pdf",
        "can you read annual reports",
    )
    voice_terms = (
        "can you hear me",
        "is my mic working",
        "did you understand what i said",
        "read this aloud",
        "generate audio",
        "speak this",
        "voice working",
    )
    document_terms = (
        "pdf",
        "document",
        "annual report",
        "uploaded report",
        "uploaded file",
        "this report",
        "this document",
        "summarize this",
        "summarise this",
        "management commentary",
        "extract investor insights",
    )
    planning_terms = (
        "i want to analyze a company",
        "i want to analyse a company",
        "help me study an annual report",
        "i want to understand a stock",
        "can you help me with financial research",
        "i want to create an investor brief",
    )
    financial_terms = (
        "market scenario",
        "market snapshot",
        "stock",
        "ticker",
        "share price",
        "latest news",
        "recent news",
        "sentiment",
        "analyze",
        "analyse",
        "compare",
        "risks for",
        "investor brief",
        "bull case",
        "bear case",
        "moving recently",
        "why is",
    )

    if _has_any(text, identity_terms):
        return "identity_question"

    if _has_any(text, capability_terms):
        return "capability_question"

    if _has_any(text, voice_terms) and not _has_any(text, financial_terms):
        return "voice_meta"

    if _is_short_casual(text):
        return "casual_chat"

    if document_ids and _has_any(text, document_terms):
        return "document_query"

    if _has_any(text, document_terms):
        return "document_query"

    if _has_any(text, planning_terms):
        return "clarification_or_planning"

    if _has_any(text, financial_terms):
        return "financial_analysis"

    if ticker and not _is_short_casual(text):
        return "financial_analysis"

    return None


def classify_intent(
    query: str,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
) -> str:
    deterministic = _deterministic_intent(query, ticker, document_ids)

    if deterministic:
        return deterministic

    try:
        validate_settings()
        llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are an intent classifier for WarrenBuffet.Ai, an AI "
                        "financial research copilot. Classify the user message into "
                        "exactly one of: casual_chat, identity_question, "
                        "capability_question, clarification_or_planning, "
                        "financial_analysis, document_query, voice_meta. Return only "
                        "the label."
                    )
                ),
                HumanMessage(
                    content=(
                        f"User message: {query}\n"
                        f"Ticker provided: {ticker or 'none'}\n"
                        f"Document IDs provided: {'yes' if document_ids else 'no'}"
                    )
                ),
            ]
        )
        label = str(response.content).strip().lower()
        label = re.sub(r"[^a-z_].*$", "", label)

        if label in VALID_INTENTS:
            return label
    except Exception:
        pass

    return "clarification_or_planning"
