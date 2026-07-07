def _clean_value(value):
    if value is None:
        return None

    try:
        if value != value:
            return None
    except TypeError:
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass

    return value


def _round_number(value, decimals: int = 2):
    value = _clean_value(value)

    if value is None:
        return None

    try:
        return round(float(value), decimals)
    except (TypeError, ValueError):
        return value


def get_market_snapshot(ticker: str) -> dict:
    try:
        import contextlib
        import io

        import yfinance as yf

        stock = yf.Ticker(ticker)

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            info = stock.info

        if not info or info.get("quoteType") in (None, "NONE"):
            return {
                "ticker": ticker,
                "data_status": "error",
                "error": "Market data could not be fetched for the provided ticker.",
            }

        current_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("postMarketPrice")
            or info.get("preMarketPrice")
        )

        current_price = _round_number(current_price)
        previous_close = _round_number(info.get("previousClose"))
        day_change = None
        day_change_percent = None

        if current_price is not None and previous_close:
            day_change = _round_number(current_price - previous_close)
            day_change_percent = _round_number((day_change / previous_close) * 100)

        snapshot = {
            "ticker": ticker,
            "current_price": current_price,
            "previous_close": previous_close,
            "day_change": day_change,
            "day_change_percent": day_change_percent,
            "open": _round_number(info.get("open")),
            "day_high": _round_number(info.get("dayHigh")),
            "day_low": _round_number(info.get("dayLow")),
            "volume": _clean_value(info.get("volume")),
            "market_cap": _clean_value(info.get("marketCap")),
            "fifty_two_week_high": _round_number(info.get("fiftyTwoWeekHigh")),
            "fifty_two_week_low": _round_number(info.get("fiftyTwoWeekLow")),
            "currency": _clean_value(info.get("currency")),
            "short_name": _clean_value(info.get("shortName") or info.get("longName")),
            "exchange": _clean_value(info.get("exchange")),
            "data_status": "ok",
        }

        has_market_value = any(
            snapshot.get(key) is not None
            for key in (
                "current_price",
                "previous_close",
                "open",
                "day_high",
                "day_low",
                "volume",
                "market_cap",
            )
        )

        if not has_market_value:
            return {
                "ticker": ticker,
                "data_status": "error",
                "error": "Market data response did not include usable quote fields.",
            }

        return snapshot
    except Exception as exc:
        return {
            "ticker": ticker,
            "data_status": "error",
            "error": str(exc) or "Market data could not be fetched.",
        }


def get_price_history(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> list[dict]:
    if not ticker:
        return []

    try:
        import contextlib
        import io

        import yfinance as yf

        stock = yf.Ticker(ticker)

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            history = stock.history(period=period, interval=interval)

        if history is None or history.empty:
            return []

        records = []

        for index, row in history.iterrows():
            date_value = index.date().isoformat() if hasattr(index, "date") else str(index)
            records.append(
                {
                    "date": date_value,
                    "open": _round_number(row.get("Open")),
                    "high": _round_number(row.get("High")),
                    "low": _round_number(row.get("Low")),
                    "close": _round_number(row.get("Close")),
                    "volume": _clean_value(row.get("Volume")),
                }
            )

        return records
    except Exception:
        return []
