from typing import Any

from app.agents.conversation_agent import generate_conversational_response
from app.agents.intent_agent import classify_intent
from app.graphs.financial_graph import run_financial_graph


CONVERSATIONAL_INTENTS = {
    "casual_chat",
    "identity_question",
    "capability_question",
    "clarification_or_planning",
    "voice_meta",
}


def _extract_sources(final_state: dict) -> list[Any]:
    sources: list[Any] = []
    market_data = final_state.get("market_data")
    news_data = final_state.get("news_data")

    if market_data and market_data.get("data_status") == "ok":
        sources.append("yfinance")

    if news_data and news_data.get("data_status") == "ok":
        for article in news_data.get("articles", []):
            url = article.get("url")
            if url and url not in sources:
                sources.append(url)

    rag_data = final_state.get("rag_data")

    if rag_data and rag_data.get("data_status") == "ok":
        seen_document_sources = set()

        for chunk in rag_data.get("chunks", []):
            source = {
                "type": "document",
                "document_id": chunk.get("document_id"),
                "filename": chunk.get("filename"),
                "page_number": chunk.get("page_number"),
                "chunk_index": chunk.get("chunk_index"),
            }
            key = (
                source["document_id"],
                source["page_number"],
                source["chunk_index"],
            )

            if key in seen_document_sources:
                continue

            seen_document_sources.add(key)
            sources.append(source)

    return sources


def handle_chat_request(
    query: str,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
) -> dict:
    intent = classify_intent(query, ticker, document_ids)

    if intent in CONVERSATIONAL_INTENTS:
        answer = generate_conversational_response(
            query=query,
            intent=intent,
            ticker=ticker,
            document_ids=document_ids,
        )
        return {
            "success": True,
            "query": query,
            "answer": answer,
            "sources": [],
            "intent": intent,
        }

    if intent == "document_query" and not document_ids:
        return {
            "success": True,
            "query": query,
            "answer": "Please upload or select a PDF first, then I can summarize or analyze it.",
            "sources": [],
            "intent": intent,
        }

    final_state = run_financial_graph(
        query=query,
        ticker=ticker,
        document_ids=document_ids,
    )

    return {
        "success": True,
        "query": query,
        "answer": final_state["answer"],
        "sources": _extract_sources(final_state),
        "intent": intent,
    }
