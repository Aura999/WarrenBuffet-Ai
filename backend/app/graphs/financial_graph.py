from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.sentiment_agent import analyze_news_sentiment
from app.agents.supervisor import route_query
from app.agents.synthesis_agent import generate_financial_response
from app.services.rag_service import retrieve_relevant_chunks
from app.tools.market_tools import get_market_snapshot
from app.tools.news_tools import get_company_news


class FinancialGraphState(TypedDict, total=False):
    query: str
    ticker: str | None
    document_ids: list[str] | None
    route: str | None
    market_data: dict | None
    news_data: dict | None
    sentiment_data: dict | None
    rag_data: dict | None
    include_market_snapshot_text: bool
    answer: str | None


def supervisor_node(state: FinancialGraphState) -> FinancialGraphState:
    return {"route": route_query(state["query"])}


def market_data_node(state: FinancialGraphState) -> FinancialGraphState:
    ticker = state.get("ticker")

    if not ticker:
        return {"market_data": None}

    return {"market_data": get_market_snapshot(ticker)}


def is_document_focused_query(query: str, document_ids: list | None = None) -> bool:
    if not document_ids:
        return False

    document_terms = (
        "document",
        "pdf",
        "annual report",
        "report",
        "uploaded",
        "from this",
        "based on this",
        "summarize this",
        "key risks",
        "management commentary",
        "extract",
    )
    normalized_query = query.lower()
    return any(term in normalized_query for term in document_terms)


def needs_news(query: str) -> bool:
    news_terms = (
        "news",
        "latest news",
        "recent news",
        "current news",
        "sentiment",
        "recent development",
        "recent developments",
        "why is stock moving",
        "why is it up",
        "why is it down",
        "why is",
        "moving recently",
        "market reaction",
    )
    normalized_query = query.lower()
    return any(term in normalized_query for term in news_terms)


def news_node(state: FinancialGraphState) -> FinancialGraphState:
    if not needs_news(state["query"]):
        return {
            "news_data": {
                "data_status": "skipped",
                "message": "News retrieval skipped for this query.",
                "articles": [],
            }
        }

    market_data = state.get("market_data") or {}
    company_name = (
        market_data.get("short_name")
        if market_data.get("data_status") == "ok"
        else None
    )

    return {
        "news_data": get_company_news(
            query=state["query"],
            ticker=state.get("ticker"),
            company_name=company_name,
        )
    }


def sentiment_node(state: FinancialGraphState) -> FinancialGraphState:
    news_data = state.get("news_data") or {}

    if news_data.get("data_status") != "ok":
        summary = (
            "No company-specific recent news articles were available for sentiment analysis."
            if news_data.get("data_status") == "empty"
            else "News sentiment skipped or unavailable."
        )
        return {
            "sentiment_data": {
                "sentiment": "unknown",
                "summary": summary,
                "key_drivers": [],
            }
        }

    return {
        "sentiment_data": analyze_news_sentiment(
            query=state["query"],
            articles=news_data.get("articles", []),
        )
    }


def _is_document_query(query: str) -> bool:
    document_terms = (
        "pdf",
        "document",
        "report",
        "annual report",
        "uploaded",
        "from this",
        "based on this",
        "summarize this",
        "management commentary",
        "risks mentioned",
        "extract from",
    )
    normalized_query = query.lower()
    return any(term in normalized_query for term in document_terms)


def rag_node(state: FinancialGraphState) -> FinancialGraphState:
    document_ids = state.get("document_ids") or []
    query = state["query"]

    if document_ids:
        broad_terms = ("brief", "comprehensive", "full analysis", "investor brief")
        k = 6 if any(term in query.lower() for term in broad_terms) else 4
        retrieved = retrieve_relevant_chunks(
            query=query,
            document_ids=document_ids,
            k=k,
        )
        return {
            "rag_data": {
                "data_status": "ok" if retrieved.get("success") else "error",
                **retrieved,
            }
        }

    if _is_document_query(query):
        broad_terms = ("brief", "comprehensive", "full analysis", "investor brief")
        k = 6 if any(term in query.lower() for term in broad_terms) else 4
        retrieved = retrieve_relevant_chunks(query=query, document_ids=None, k=k)

        if retrieved.get("success"):
            return {
                "rag_data": {
                    "data_status": "ok",
                    **retrieved,
                }
            }

        return {
            "rag_data": {
                "data_status": "missing_documents",
                "message": "No uploaded documents were provided for this request.",
                "chunks": [],
            }
        }

    return {"rag_data": None}


def synthesis_node(state: FinancialGraphState) -> FinancialGraphState:
    answer = generate_financial_response(
        query=state["query"],
        ticker=state.get("ticker"),
        route=state.get("route") or "general_financial_analysis",
        market_data=state.get("market_data"),
        news_data=state.get("news_data"),
        sentiment_data=state.get("sentiment_data"),
        rag_data=state.get("rag_data"),
        include_market_snapshot_text=state.get("include_market_snapshot_text", True),
    )
    return {"answer": answer}


def build_financial_graph():
    graph = StateGraph(FinancialGraphState)

    graph.add_node("supervisor_node", supervisor_node)
    graph.add_node("market_data_node", market_data_node)
    graph.add_node("news_node", news_node)
    graph.add_node("sentiment_node", sentiment_node)
    graph.add_node("rag_node", rag_node)
    graph.add_node("synthesis_node", synthesis_node)

    graph.add_edge(START, "supervisor_node")
    graph.add_edge("supervisor_node", "market_data_node")
    graph.add_edge("market_data_node", "news_node")
    graph.add_edge("news_node", "sentiment_node")
    graph.add_edge("sentiment_node", "rag_node")
    graph.add_edge("rag_node", "synthesis_node")
    graph.add_edge("synthesis_node", END)

    return graph.compile()


def run_financial_graph(
    query: str,
    ticker: str | None = None,
    document_ids: list[str] | None = None,
    include_market_snapshot_text: bool = True,
) -> dict:
    graph = build_financial_graph()
    return graph.invoke(
        {
            "query": query,
            "ticker": ticker,
            "document_ids": document_ids,
            "include_market_snapshot_text": include_market_snapshot_text,
        }
    )
