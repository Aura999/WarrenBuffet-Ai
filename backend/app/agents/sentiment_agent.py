import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import OPENAI_MODEL, validate_settings


VALID_SENTIMENTS = {"positive", "negative", "neutral", "mixed", "unknown"}


def _unknown_sentiment() -> dict:
    return {
        "sentiment": "unknown",
        "summary": "No company-specific recent news articles were available for sentiment analysis.",
        "key_drivers": [],
    }


def _article_context(articles: list) -> str:
    rows = []

    for index, article in enumerate(articles[:5], start=1):
        rows.append(
            "\n".join(
                [
                    f"Article {index}",
                    f"Title: {article.get('title')}",
                    f"Source: {article.get('source')}",
                    f"Published date: {article.get('published_date')}",
                    f"Snippet: {article.get('content')}",
                    f"URL: {article.get('url')}",
                ]
            )
        )

    return "\n\n".join(rows)


def analyze_news_sentiment(query: str, articles: list) -> dict:
    if not articles:
        return _unknown_sentiment()

    validate_settings()

    llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    prompt = f"""
User query: {query}

Analyze sentiment using only the supplied article titles and snippets. Do not invent news or facts.
Classify sentiment as exactly one of: positive, negative, neutral, mixed, unknown.
Return only valid JSON with this shape:
{{
  "sentiment": "positive|negative|neutral|mixed|unknown",
  "summary": "short summary",
  "key_drivers": ["driver 1", "driver 2", "driver 3"]
}}

Articles:
{_article_context(articles)}
"""

    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are a financial news sentiment analyst. Analyze only the "
                    "provided article titles and snippets. Return strict JSON."
                )
            ),
            HumanMessage(content=prompt),
        ]
    )

    content = str(response.content).strip()
    json_match = re.search(r"\{.*\}", content, flags=re.DOTALL)

    try:
        data = json.loads(json_match.group(0) if json_match else content)
    except json.JSONDecodeError:
        return {
            "sentiment": "unknown",
            "summary": "News sentiment could not be parsed reliably.",
            "key_drivers": [],
        }

    sentiment = data.get("sentiment", "unknown")
    if sentiment not in VALID_SENTIMENTS:
        sentiment = "unknown"

    key_drivers = data.get("key_drivers", [])
    if not isinstance(key_drivers, list):
        key_drivers = []

    return {
        "sentiment": sentiment,
        "summary": data.get("summary") or "No sentiment summary was available.",
        "key_drivers": [str(driver) for driver in key_drivers[:3]],
    }
