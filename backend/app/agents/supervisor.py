def route_query(query: str) -> str:
    normalized_query = query.lower()

    risk_keywords = ("risk", "risks", "concern", "concerns", "bear case")
    company_keywords = (
        "analyze",
        "analysis",
        "company",
        "stock",
        "business",
        "investor",
        "investment",
        "research",
        "brief",
    )

    if any(keyword in normalized_query for keyword in risk_keywords):
        return "risk_analysis"

    if any(keyword in normalized_query for keyword in company_keywords):
        return "company_analysis"

    return "general_financial_analysis"
