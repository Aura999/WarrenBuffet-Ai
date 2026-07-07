import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import OPENAI_MODEL, validate_settings
from app.core.observability import summarize_answer_output, traceable_if_enabled


BRAND_IDENTITY = (
    "WarrenBuffet.Ai, an AI-powered financial research copilot designed and "
    "built by Satyam Mishra"
)


def _process_conversation_trace_inputs(inputs: dict) -> dict:
    return {
        "query": inputs.get("query"),
        "intent": inputs.get("intent"),
    }


def _fallback_response(intent: str, query: str = "") -> str:
    if intent == "identity_question":
        normalized_query = query.lower()

        if any(
            term in normalized_query
            for term in ("chatgpt", "openai", "gpt", "model")
        ):
            return (
                "I'm WarrenBuffet.Ai, designed and built by Satyam Mishra. I use "
                "AI models behind the scenes, but my role here is to help with "
                "financial research, document analysis, market insights, and "
                "investor-style summaries."
            )

        return (
            "I'm WarrenBuffet.Ai, an AI-powered financial research copilot "
            "designed and built by Satyam Mishra. I help analyze companies, "
            "market data, news sentiment, annual reports, and investor-style "
            "research questions."
        )

    if intent == "capability_question":
        return (
            "I can analyze companies, fetch market snapshots, summarize company "
            "news and sentiment, reason over uploaded annual reports or PDFs, "
            "generate investor briefs, and support voice-based financial research."
        )

    if intent == "voice_meta":
        return (
            "I can work with voice questions through the Voice Assistant: record "
            "or upload audio, I transcribe it, answer through the research "
            "pipeline when needed, and can generate spoken responses."
        )

    if intent == "clarification_or_planning":
        return (
            "Sure. Which company or ticker should we analyze? You can also "
            "upload an annual report if you want document-grounded insights."
        )

    return (
        "Hi, I'm WarrenBuffet.Ai. Tell me which company, ticker, market topic, "
        "or uploaded report you want to analyze."
    )


def _remove_identity_leakage(text: str, intent: str, query: str = "") -> str:
    forbidden_patterns = (
        r"\bI\s*(?:am|'m)\s+ChatGPT\b",
        r"\bI\s*(?:am|'m)\s+OpenAI\b",
        r"\bI\s*(?:am|'m)\s+(?:a\s+)?GPT\b",
        r"\bI\s*(?:am|'m)\s+an\s+OpenAI\s+model\b",
        r"\bChatGPT\b",
        r"\bOpenAI\b",
        r"\bGPT\b",
    )

    cleaned = text
    for pattern in forbidden_patterns:
        cleaned = re.sub(pattern, "WarrenBuffet.Ai", cleaned, flags=re.IGNORECASE)

    if re.search(r"warrenbuffet\.ai", cleaned, flags=re.IGNORECASE):
        return cleaned.strip()

    if intent in {"identity_question", "capability_question"}:
        return _fallback_response(intent, query)

    return cleaned.strip()


def generate_conversational_response(
    query: str,
    intent: str,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
) -> str:
    return _generate_conversational_response_traced(query, intent, ticker, document_ids)


@traceable_if_enabled(
    name="Conversation Agent",
    process_inputs=_process_conversation_trace_inputs,
    process_outputs=summarize_answer_output,
)
def _generate_conversational_response_traced(
    query: str,
    intent: str,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
) -> str:
    try:
        validate_settings()
        llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.2)
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are WarrenBuffet.Ai, an AI-powered financial research "
                        "copilot designed and built by Satyam Mishra. You help users "
                        "analyze companies, market data, news sentiment, annual "
                        "reports, and investor-style research questions. Do not "
                        "introduce yourself as ChatGPT, OpenAI, GPT, or any "
                        "underlying model provider. If asked who you are, say you "
                        "are WarrenBuffet.Ai, designed and built by Satyam Mishra. "
                        "Keep responses concise, friendly, and useful."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Intent: {intent}\n"
                        f"User query: {query}\n"
                        f"Ticker provided: {ticker or 'none'}\n"
                        f"Document IDs selected: {'yes' if document_ids else 'no'}\n\n"
                        "Response rules:\n"
                        "- casual_chat: short, friendly, ask what the user wants to analyze.\n"
                        "- identity_question: give the branded identity.\n"
                        "- capability_question: briefly list capabilities.\n"
                        "- clarification_or_planning: ask a useful follow-up question.\n"
                        "- voice_meta: explain voice capability briefly.\n"
                        "- Do not produce a financial report in conversational mode."
                    )
                ),
            ]
        )
        answer = str(response.content).strip()
        return _remove_identity_leakage(answer, intent, query) or _fallback_response(intent, query)
    except Exception:
        return _fallback_response(intent, query)
