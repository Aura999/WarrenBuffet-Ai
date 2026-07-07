from app.core.config import TAVILY_API_KEY, validate_tavily_settings


COMPANY_ALIASES = {
    "RELIANCE.NS": [
        "reliance industries",
        "reliance industries ltd",
        "ril",
        "reliance jio",
        "jio platforms",
        "jio",
        "jiomart",
        "mukesh ambani",
        "reliance retail",
    ],
    "ETERNAL.NS": [
        "eternal",
        "zomato",
        "blinkit",
        "deepinder goyal",
        "hyperpure",
    ],
    "ZOMATO.NS": [
        "zomato",
        "eternal",
        "blinkit",
        "deepinder goyal",
        "hyperpure",
    ],
    "INFY.NS": [
        "infosys",
        "infy",
        "salil parekh",
    ],
    "TCS.NS": [
        "tcs",
        "tata consultancy services",
    ],
    "HDFCBANK.NS": [
        "hdfc bank",
        "hdfcbank",
    ],
}


def _ticker_base(ticker: str | None) -> str | None:
    if not ticker:
        return None

    return ticker.split(".")[0].lower()


def _known_aliases(ticker: str | None, company_name: str | None = None) -> list[str]:
    aliases = []
    ticker_key = ticker.upper() if ticker else None
    ticker_base = _ticker_base(ticker)

    if company_name:
        aliases.append(company_name)

    if ticker_key in COMPANY_ALIASES:
        aliases.extend(COMPANY_ALIASES[ticker_key])

    if ticker_base:
        aliases.append(ticker_base)

    deduped = []
    seen = set()

    for alias in aliases:
        normalized = alias.strip().lower()

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)
        deduped.append(alias.strip())

    return deduped


def _company_keywords(ticker: str | None, company_name: str | None = None) -> list[str]:
    ticker_key = ticker.upper() if ticker else None
    ticker_base = _ticker_base(ticker)

    if ticker_key in COMPANY_ALIASES:
        keywords = [keyword.lower() for keyword in COMPANY_ALIASES[ticker_key]]
        keywords.append(ticker_key.lower())

        if ticker_base:
            keywords.append(ticker_base)

        return _dedupe_keywords(keywords)

    keywords = []

    for alias in _known_aliases(ticker, company_name):
        keywords.extend(alias.lower().split())

    return _dedupe_keywords(keywords)


def _dedupe_keywords(keywords: list[str]) -> list[str]:
    ignored_tokens = {"limited", "ltd", "inc", "corp", "corporation", "company", "co"}
    deduped = []
    seen = set()

    for keyword in keywords:
        normalized = keyword.strip().lower().strip(".,()[]")

        if len(normalized) < 3 or normalized in ignored_tokens or normalized in seen:
            continue

        seen.add(normalized)
        deduped.append(normalized)

    return deduped


def _build_news_query(
    query: str,
    ticker: str | None = None,
    company_name: str | None = None,
) -> str:
    if ticker:
        aliases = " ".join(_known_aliases(ticker, company_name))

        if aliases:
            return (
                f"{aliases} {ticker} latest news earnings results annual report "
                "risks business update stock India"
            )

        return (
            f"{ticker} latest news earnings results annual report risks business "
            "update stock India"
        )

    return f"{query} latest financial news market sentiment"


def _normalize_article(result: dict) -> dict:
    return {
        "title": result.get("title") or "Untitled",
        "url": result.get("url"),
        "content": result.get("content") or result.get("raw_content") or "",
        "source": result.get("source") or result.get("url"),
        "published_date": result.get("published_date") or result.get("publishedDate"),
    }


def _article_matches_reliance(article: dict) -> bool:
    import re

    title = str(article.get("title") or "").lower()
    url = str(article.get("url") or "").lower()
    content = str(article.get("content") or "").lower()
    text = f"{title} {url} {content}"
    strong_aliases = (
        "reliance industries",
        "reliance industries ltd",
        "ril",
        "reliance jio",
        "jio platforms",
        "jio",
        "reliance retail",
        "mukesh ambani",
    )
    company_context_terms = (
        "industries",
        "ltd",
        "jio",
        "retail",
        "ambani",
        "oil-to-chemicals",
        "petrochemicals",
        "nse",
        "bse",
        "ril",
    )
    generic_reliance_patterns = (
        r"\breliance on\b",
        r"\breduce reliance\b",
        r"\breducing reliance\b",
        r"\bless reliance\b",
        r"\bdependence/reliance\b",
        r"\breliance/dependence\b",
        r"\breliance on u\.s\.\b",
        r"\breliance on us\b",
        r"\breliance on china\b",
        r"\breliance on oil\b",
        r"\breliance on imports\b",
    )

    if any(alias in text for alias in strong_aliases):
        return True

    if not re.search(r"\breliance\b", text):
        return False

    if any(re.search(pattern, text) for pattern in generic_reliance_patterns):
        return False

    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in company_context_terms)


def _article_matches_company(
    article: dict,
    keywords: list[str],
    ticker: str | None = None,
) -> bool:
    if ticker and ticker.upper() == "RELIANCE.NS":
        return _article_matches_reliance(article)

    if not keywords:
        return True

    title = str(article.get("title") or "").lower()
    url = str(article.get("url") or "").lower()
    content = str(article.get("content") or "").lower()
    title_url = f"{title} {url}"
    broad_market_terms = (
        "india stocks",
        "nifty",
        "sensex",
        "global markets",
        "forex",
        "payroll",
        "middle east",
        "fed",
        "wall street",
        "markets higher",
        "markets lower",
        "stocks higher",
        "stocks lower",
    )

    if any(_contains_company_keyword(title_url, keyword) for keyword in keywords):
        return True

    matched_content_keywords = {
        keyword
        for keyword in keywords
        if _contains_company_keyword(content, keyword)
    }

    if any(term in title for term in broad_market_terms):
        return False

    return len(matched_content_keywords) >= 2


def _contains_company_keyword(text: str, keyword: str) -> bool:
    import re

    normalized_text = text.lower()
    normalized_keyword = keyword.lower().strip()

    if not normalized_keyword:
        return False

    if normalized_keyword.isalnum():
        return re.search(rf"\b{re.escape(normalized_keyword)}\b", normalized_text) is not None

    return normalized_keyword in normalized_text


def get_company_news(
    query: str,
    ticker: str | None = None,
    company_name: str | None = None,
    max_results: int = 5,
) -> dict:
    search_query = _build_news_query(query, ticker, company_name)
    company_keywords = _company_keywords(ticker, company_name)

    try:
        validate_tavily_settings()

        from tavily import TavilyClient

        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(
            query=search_query,
            topic="news",
            search_depth="basic",
            max_results=max(max_results * 2, 10) if company_keywords else max_results,
            include_answer=False,
            include_raw_content=False,
        )

        articles = [
            _normalize_article(result)
            for result in response.get("results", [])
            if result.get("title") or result.get("content") or result.get("url")
        ]
        articles = [
            article
            for article in articles
            if _article_matches_company(article, company_keywords, ticker)
        ][:max_results]

        if not articles:
            return {
                "data_status": "empty",
                "query": search_query,
                "articles": [],
                "message": "No company-specific recent news found.",
            }

        return {
            "data_status": "ok",
            "query": search_query,
            "articles": articles,
        }
    except Exception as exc:
        return {
            "data_status": "error",
            "query": search_query,
            "error": str(exc) or "News data could not be fetched.",
            "articles": [],
        }
