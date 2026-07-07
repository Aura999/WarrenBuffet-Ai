from typing import Any

from app.agents.conversation_agent import generate_conversational_response
from app.agents.intent_agent import classify_intent
from app.core.config import LANGSMITH_PROJECT
from app.core.observability import logger, traceable_if_enabled
from app.graphs.financial_graph import run_financial_graph
from app.tools.market_tools import get_price_history


CONVERSATIONAL_INTENTS = {
    "casual_chat",
    "identity_question",
    "capability_question",
    "clarification_or_planning",
    "voice_meta",
}


def _process_chat_trace_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    document_ids = inputs.get("document_ids") or []
    return {
        "query": inputs.get("query"),
        "ticker": inputs.get("ticker"),
        "document_ids_count": len(document_ids),
        "has_documents": bool(document_ids),
        "request_type": inputs.get("request_type"),
        "project": LANGSMITH_PROJECT,
    }


def _process_chat_trace_outputs(output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {"output_type": type(output).__name__}

    answer = str(output.get("answer") or "")
    visuals = output.get("visuals") or {}
    return {
        "success": output.get("success"),
        "intent": output.get("intent"),
        "answer_length": len(answer),
        "sources_count": len(output.get("sources") or []),
        "has_market_snapshot": bool(visuals.get("market_snapshot")),
        "has_price_history": bool(visuals.get("price_history")),
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
            if not url:
                continue

            source = {
                "type": "news",
                "title": article.get("title"),
                "url": url,
                "source": article.get("source"),
            }

            if not any(
                isinstance(existing, dict)
                and existing.get("type") == "news"
                and existing.get("url") == url
                for existing in sources
            ):
                sources.append(source)

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


def _infer_ticker_from_query(query: str, ticker: str | None = None) -> str | None:
    if ticker:
        return ticker

    normalized = query.lower()
    reliance_terms = (
        "reliance industries",
        "reliance industries ltd",
        "ril",
        "reliance jio",
        "jio platforms",
        "reliance retail",
        "mukesh ambani",
    )

    if any(term in normalized for term in reliance_terms):
        return "RELIANCE.NS"

    return ticker


def _build_market_snapshot_visual(market_data: dict | None) -> dict | None:
    if not market_data or market_data.get("data_status") != "ok":
        return None

    return {
        "ticker": market_data.get("ticker"),
        "company_name": market_data.get("short_name"),
        "current_price": market_data.get("current_price"),
        "previous_close": market_data.get("previous_close"),
        "day_change": market_data.get("day_change"),
        "day_change_pct": market_data.get("day_change_percent"),
        "open": market_data.get("open"),
        "day_high": market_data.get("day_high"),
        "day_low": market_data.get("day_low"),
        "volume": market_data.get("volume"),
        "market_cap": market_data.get("market_cap"),
        "fifty_two_week_high": market_data.get("fifty_two_week_high"),
        "fifty_two_week_low": market_data.get("fifty_two_week_low"),
        "currency": market_data.get("currency"),
        "exchange": market_data.get("exchange"),
        "data_source": "yfinance",
    }


def _build_visuals(final_state: dict, ticker: str | None = None) -> dict | None:
    market_snapshot = _build_market_snapshot_visual(final_state.get("market_data"))
    price_history = get_price_history(ticker) if ticker else []

    visuals = {
        "market_snapshot": market_snapshot,
        "price_history": price_history,
    }
    available_visuals = {
        key: value
        for key, value in visuals.items()
        if value
    }

    return available_visuals or None


def handle_chat_request(
    query: str,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
    request_type: str = "text_chat",
) -> dict:
    return _handle_chat_request_traced(
        query=query,
        ticker=ticker,
        document_ids=document_ids,
        request_type=request_type,
    )


@traceable_if_enabled(
    name="WarrenBuffetAi Chat Request",
    metadata={"project": LANGSMITH_PROJECT},
    process_inputs=_process_chat_trace_inputs,
    process_outputs=_process_chat_trace_outputs,
)
def _handle_chat_request_traced(
    query: str,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
    request_type: str = "text_chat",
) -> dict:
    intent = classify_intent(query, ticker, document_ids)
    resolved_ticker = _infer_ticker_from_query(query, ticker)
    logger.info(
        "chat_request intent=%s request_type=%s ticker=%s resolved_ticker=%s document_ids_count=%s",
        intent,
        request_type,
        ticker,
        resolved_ticker,
        len(document_ids or []),
    )

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
            "visuals": None,
            "intent": intent,
        }

    if intent == "document_query" and not document_ids:
        return {
            "success": True,
            "query": query,
            "answer": "Please upload or select a PDF first, then I can summarize or analyze it.",
            "sources": [],
            "visuals": None,
            "intent": intent,
        }

    final_state = run_financial_graph(
        query=query,
        ticker=resolved_ticker,
        document_ids=document_ids,
        include_market_snapshot_text=False,
    )
    visuals = _build_visuals(final_state, resolved_ticker)
    logger.info(
        "chat_request_completed intent=%s resolved_ticker=%s visuals_generated=%s",
        intent,
        resolved_ticker,
        bool(visuals),
    )

    return {
        "success": True,
        "query": query,
        "answer": final_state["answer"],
        "sources": _extract_sources(final_state),
        "visuals": visuals,
        "intent": intent,
    }
