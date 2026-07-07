from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import OPENAI_MODEL, validate_settings
from app.core.observability import logger, summarize_answer_output, traceable_if_enabled


SYSTEM_PROMPT = """You are WarrenBuffet.Ai, an AI-powered financial research copilot designed and built by Satyam Mishra. You help users understand companies, markets, financial risks, and investment narratives. You provide structured research-style analysis, but you do not provide personalized financial advice or guaranteed buy/sell recommendations. Do not introduce yourself as ChatGPT, OpenAI, GPT, or any underlying model provider. Be clear, concise, and analytical."""

LIVE_DATA_WARNING = "Live market data is connected only through yfinance in this phase and may be delayed."


def _asks_for_live_data(query: str) -> bool:
    live_data_terms = (
        "current",
        "latest",
        "today",
        "live",
        "real-time",
        "realtime",
        "now",
        "price",
        "news",
    )
    normalized_query = query.lower()
    return any(term in normalized_query for term in live_data_terms)


def _display_value(value, prefix: str | None = None, suffix: str | None = None) -> str:
    if value is None:
        return "N/A"

    text = str(value)

    if prefix:
        text = f"{prefix} {text}"

    if suffix:
        text = f"{text}{suffix}"

    return text


def format_market_snapshot(market_data: dict) -> str:
    currency = market_data.get("currency")

    return f"""### Market Snapshot
- Company: {_display_value(market_data.get("short_name"))}
- Ticker: {_display_value(market_data.get("ticker"))}
- Current Price: {_display_value(market_data.get("current_price"), currency)}
- Previous Close: {_display_value(market_data.get("previous_close"), currency)}
- Day Change: {_display_value(market_data.get("day_change"), currency)}
- Day Change %: {_display_value(market_data.get("day_change_percent"), suffix="%")}
- Open: {_display_value(market_data.get("open"), currency)}
- Day High: {_display_value(market_data.get("day_high"), currency)}
- Day Low: {_display_value(market_data.get("day_low"), currency)}
- Volume: {_display_value(market_data.get("volume"))}
- Market Cap: {_display_value(market_data.get("market_cap"))}
- 52-Week High: {_display_value(market_data.get("fifty_two_week_high"), currency)}
- 52-Week Low: {_display_value(market_data.get("fifty_two_week_low"), currency)}
- Currency: {_display_value(currency)}
- Exchange: {_display_value(market_data.get("exchange"))}
- Data Source: yfinance
- Note: Market data may be delayed."""


def format_news_snapshot(news_data: dict, sentiment_data: dict | None) -> str:
    sentiment_data = sentiment_data or {}
    articles = news_data.get("articles", [])
    sources = [
        article.get("url")
        for article in articles
        if article.get("url")
    ]
    key_drivers = sentiment_data.get("key_drivers") or []

    drivers_text = (
        "; ".join(str(driver) for driver in key_drivers)
        if key_drivers
        else "N/A"
    )
    sources_text = "; ".join(sources) if sources else "N/A"

    return f"""### News & Sentiment Snapshot
- Overall Sentiment: {_display_value(sentiment_data.get("sentiment"))}
- Key News Drivers: {drivers_text}
- News Summary: {_display_value(sentiment_data.get("summary"))}
- Sources: {sources_text}
- Data Source: Tavily search results
- Note: News context is based on retrieved company-specific search results and may be incomplete."""


def _format_news_context(news_data: dict) -> str:
    article_lines = []

    for index, article in enumerate(news_data.get("articles", [])[:5], start=1):
        article_lines.append(
            "\n".join(
                [
                    f"Article {index}:",
                    f"- Title: {article.get('title')}",
                    f"- Source: {article.get('source')}",
                    f"- Published date: {article.get('published_date')}",
                    f"- Snippet/content: {article.get('content')}",
                    f"- URL: {article.get('url')}",
                ]
            )
        )

    return "\n\n".join(article_lines)


def _format_document_insights(rag_data: dict) -> str:
    chunks = rag_data.get("chunks", [])
    pages = []

    for chunk in chunks:
        label = f"{chunk.get('filename')} page {chunk.get('page_number')}"

        if label not in pages:
            pages.append(label)

    return f"""### Document Insights
- Key document-backed findings: See retrieved document excerpts cited in the analysis.
- Relevant pages: {_display_value('; '.join(pages) if pages else None)}
- Important caveats: Only relevant excerpts were retrieved. The answer should not claim to cover the entire document unless the retrieved excerpts support that."""


def _format_document_context(rag_data: dict) -> str:
    context_blocks = []

    for index, chunk in enumerate(rag_data.get("chunks", [])[:6], start=1):
        context_blocks.append(
            "\n".join(
                [
                    f"[Document Source {index}]",
                    f"Filename: {chunk.get('filename')}",
                    f"Page: {chunk.get('page_number')}",
                    f"Chunk: {chunk.get('chunk_index')}",
                    f"Text: {chunk.get('text')}",
                ]
            )
        )

    return "\n\n".join(context_blocks)


def _strip_generated_snapshots(text: str) -> str:
    snapshot_headings = (
        "### Market Snapshot",
        "### News & Sentiment Snapshot",
        "### Document Insights",
    )
    stripped = text.strip()

    if stripped.startswith(snapshot_headings):
        next_section_index = stripped.find("### 1.")

        if next_section_index != -1:
            return stripped[next_section_index:].lstrip()

    for heading in ("### Market Snapshot", "### News & Sentiment Snapshot"):
        while heading in stripped:
            start = stripped.find(heading)
            next_heading = stripped.find("### ", start + len(heading))

            if next_heading == -1:
                stripped = stripped[:start].rstrip()
                break

            stripped = (stripped[:start] + stripped[next_heading:]).strip()

    return stripped


def _process_synthesis_trace_inputs(inputs: dict) -> dict:
    market_data = inputs.get("market_data") or {}
    news_data = inputs.get("news_data") or {}
    rag_data = inputs.get("rag_data") or {}
    return {
        "query": inputs.get("query"),
        "ticker": inputs.get("ticker"),
        "route": inputs.get("route"),
        "has_market_data": market_data.get("data_status") == "ok",
        "has_news_data": news_data.get("data_status") == "ok",
        "has_rag_data": rag_data.get("data_status") == "ok",
    }


@traceable_if_enabled(
    name="Synthesis Agent",
    process_inputs=_process_synthesis_trace_inputs,
    process_outputs=summarize_answer_output,
)
def generate_financial_response(
    query: str,
    ticker: str | None = None,
    route: str = "general_financial_analysis",
    market_data: dict | None = None,
    news_data: dict | None = None,
    sentiment_data: dict | None = None,
    rag_data: dict | None = None,
    include_market_snapshot_text: bool = True,
) -> str:
    validate_settings()

    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.2)

    ticker_context = f"\nTicker provided by user: {ticker}" if ticker else ""
    market_snapshot_text = None
    news_snapshot_text = None
    news_unavailable_text = None
    document_insights_text = None

    if market_data and market_data.get("data_status") == "ok":
        market_snapshot_text = (
            format_market_snapshot(market_data)
            if include_market_snapshot_text
            else None
        )
        market_data_context = f"""

MARKET DATA CONTEXT:
source: yfinance
data_note: Market data from yfinance may be delayed.
ticker: {market_data.get("ticker")}
company: {market_data.get("short_name")}
current_price: {market_data.get("current_price")}
previous_close: {market_data.get("previous_close")}
day_change: {market_data.get("day_change")}
day_change_percent: {market_data.get("day_change_percent")}
open: {market_data.get("open")}
day_high: {market_data.get("day_high")}
day_low: {market_data.get("day_low")}
volume: {market_data.get("volume")}
market_cap: {market_data.get("market_cap")}
52_week_high: {market_data.get("fifty_two_week_high")}
52_week_low: {market_data.get("fifty_two_week_low")}
currency: {market_data.get("currency")}
exchange: {market_data.get("exchange")}
"""
    elif market_data and market_data.get("data_status") == "error":
        market_data_context = f"""

MARKET DATA SNAPSHOT:
source: yfinance
data_status: unavailable
error: {market_data.get("error")}
"""
    else:
        market_data_context = "\nNo ticker was provided, so no market data snapshot is available."

    if news_data and news_data.get("data_status") == "ok":
        news_snapshot_text = format_news_snapshot(news_data, sentiment_data)
        news_context = f"""

RECENT COMPANY-SPECIFIC NEWS CONTEXT:
{_format_news_context(news_data)}
"""
    elif news_data and news_data.get("data_status") == "empty":
        news_unavailable_text = """### News & Sentiment Snapshot
- Company-specific recent news could not be fetched in this run.
- Data Source: Tavily search attempted
- Note: Irrelevant/general news results were filtered out."""
        news_context = f"""

RECENT NEWS CONTEXT:
Company-specific recent news could not be fetched in this run.
Message: {news_data.get("message") or "No company-specific recent news found."}
Query: {news_data.get("query")}
"""
    elif news_data and news_data.get("data_status") == "error":
        news_unavailable_text = "Company-specific recent news could not be fetched in this run."
        news_context = f"""

RECENT NEWS CONTEXT:
Recent news could not be fetched in this run.
Error: {news_data.get("error")}
"""
    elif news_data and news_data.get("data_status") == "skipped":
        news_context = "\nNEWS CONTEXT: News retrieval skipped for this query."
    else:
        news_context = "\nNEWS CONTEXT: not requested"

    if sentiment_data:
        sentiment_context = f"""

NEWS SENTIMENT:
- Sentiment: {sentiment_data.get("sentiment")}
- Summary: {sentiment_data.get("summary")}
- Key Drivers: {sentiment_data.get("key_drivers")}
"""
    else:
        sentiment_context = "\nNEWS SENTIMENT: unavailable"

    if rag_data and rag_data.get("data_status") == "ok" and rag_data.get("chunks"):
        document_insights_text = _format_document_insights(rag_data)
        document_context = f"""

DOCUMENT INSIGHTS TO INCLUDE UNCHANGED AFTER AVAILABLE MARKET/NEWS SNAPSHOTS:
{document_insights_text}

DOCUMENT CONTEXT:
{_format_document_context(rag_data)}
"""
    elif rag_data and rag_data.get("data_status") == "missing_documents":
        document_context = """

DOCUMENT CONTEXT:
No uploaded document was provided. Please upload a PDF first, then ask me to summarize or analyze it.
"""
    elif rag_data and rag_data.get("data_status") == "error":
        document_context = f"""

DOCUMENT CONTEXT:
Document retrieval was unavailable.
Error: {rag_data.get("error")}
"""
    else:
        document_context = "\nDOCUMENT CONTEXT: not requested"

    live_data_context = (
        f"\nThe user may be asking for current market information. Explain that "
        f"market data comes from yfinance and may be delayed."
        if _asks_for_live_data(query) and market_data and market_data.get("data_status") == "ok"
        else ""
    )
    market_snapshot_response_instruction = (
        '- Do not create a Market Snapshot section. The UI already displays structured '
        'Market Snapshot cards. Do not repeat the full market snapshot table/list in '
        'the answer. Refer to it briefly as "the market snapshot above" and focus on '
        'interpretation, drivers, risks, bull case, bear case, and what to watch. Do '
        'not repeat Current Price, Previous Close, Day Change, Open, Day High, Day '
        'Low, Volume, Market Cap, 52W High, 52W Low, Currency, or Exchange as a '
        'snapshot list.'
        if not include_market_snapshot_text
        else "- Do not create a Market Snapshot section. It has already been generated and will be prepended separately. Start your response after the Market Snapshot."
    )

    user_prompt = f"""
Route: {route}
User query: {query}{ticker_context}{market_data_context}{news_context}{sentiment_context}{document_context}{live_data_context}

Create a structured financial research-style response. Use this structure where relevant:

1. Executive Summary
2. Business / Market Context
3. Key Drivers
4. Key Risks
5. Bull Case
6. Bear Case
7. What To Watch Next
8. Disclaimer: This is research assistance, not financial advice.

Important constraints:
- Start your response with "### 1. Executive Summary" unless there is a stronger analysis heading needed.
{market_snapshot_response_instruction}
- Do not create a News & Sentiment Snapshot section. It has already been generated and will be prepended separately when relevant. Use the news context in the analysis if relevant.
- Do not create a Document Insights section. It has already been generated and will be prepended separately when document context exists.
- If no successful Tavily news context is provided, say "Company-specific recent news could not be fetched in this run." in the analysis where relevant.
- If no uploaded document was provided for a document question, say: "No uploaded document was provided. Please upload a PDF first, then ask me to summarize or analyze it."
- Use the market data snapshot where relevant.
- Use the market data, news context, and sentiment analysis where relevant.
- Use the uploaded document context where relevant.
- If answering based on the document, cite sources inline using labels like [Document Source 1], [Document Source 2].
- Clearly mention that market data comes from yfinance and may be delayed when market data is included.
- Do not overstate this as real-time data. Mention that yfinance market data may be delayed.
- Do not invent missing financial metrics.
- Do not invent current events or news.
- Do not let unavailable or filtered-out news affect the Executive Summary, Key Drivers, Risks, Bull Case, Bear Case, or What To Watch Next.
- Do not invent document facts or page numbers.
- If document context is insufficient, say so clearly.
- If document context conflicts with generic prior knowledge, prefer document context and say "based on the uploaded document".
- Do not claim to have read the whole document unless the retrieved chunks support the answer.
- Mention if only relevant excerpts were retrieved.
- If market data is unavailable, say so clearly.
- If news context is unavailable, say news data could not be fetched.
- This phase includes retrieved Tavily news context, but not full current financial statements.
- Do not pretend to know real-time prices beyond the provided yfinance snapshot.
- Do not present this as investment advice.
- Keep the analysis concise and useful for financial research.
"""

    response = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
    )

    analysis = str(response.content).strip()
    snapshots = [
        text
        for text in (
            market_snapshot_text,
            news_snapshot_text,
            news_unavailable_text,
            document_insights_text,
        )
        if text
    ]

    if snapshots:
        analysis = _strip_generated_snapshots(analysis)
        answer = "\n\n".join([*snapshots, analysis])
        logger.info(
            "synthesis has_market_data=%s has_news_data=%s has_rag_data=%s answer_length=%s",
            bool(market_data and market_data.get("data_status") == "ok"),
            bool(news_data and news_data.get("data_status") == "ok"),
            bool(rag_data and rag_data.get("data_status") == "ok"),
            len(answer),
        )
        return answer

    analysis = _strip_generated_snapshots(analysis)

    logger.info(
        "synthesis has_market_data=%s has_news_data=%s has_rag_data=%s answer_length=%s",
        bool(market_data and market_data.get("data_status") == "ok"),
        bool(news_data and news_data.get("data_status") == "ok"),
        bool(rag_data and rag_data.get("data_status") == "ok"),
        len(analysis),
    )
    return analysis


def synthesize_response(query: str) -> str:
    return generate_financial_response(query)
