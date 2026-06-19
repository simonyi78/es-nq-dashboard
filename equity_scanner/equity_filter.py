"""Screen equities for $200M-$2B market caps sitting in a 50-day consolidation base."""

import os

import pandas as pd
import yfinance as yf

MIN_MARKET_CAP = 200_000_000
MAX_MARKET_CAP = 2_000_000_000
CONSOLIDATION_DAYS = 50
MAX_RANGE_PCT = 15.0  # (50d high - 50d low) / 50d low, as a percent


def _consolidation_range(hist: pd.DataFrame, days: int = CONSOLIDATION_DAYS) -> float | None:
    """Return the high/low range of the trailing `days` bars as a percent of the low."""
    if len(hist) < days:
        return None

    window = hist.tail(days)
    low = window["Low"].min()
    high = window["High"].max()
    if low <= 0:
        return None

    return round((high - low) / low * 100, 2)


def screen_ticker(ticker: str) -> dict | None:
    """Return a result dict if `ticker` matches the cap + consolidation criteria, else None."""
    t = yf.Ticker(ticker)
    info = t.info

    market_cap = info.get("marketCap")
    if market_cap is None or not (MIN_MARKET_CAP <= market_cap <= MAX_MARKET_CAP):
        return None

    hist = t.history(period="3mo", interval="1d").dropna(subset=["Close"])
    range_pct = _consolidation_range(hist)
    if range_pct is None or range_pct > MAX_RANGE_PCT:
        return None

    window = hist.tail(CONSOLIDATION_DAYS)
    low_50d = float(window["Low"].min())
    high_50d = float(window["High"].max())
    price = round(float(hist["Close"].iloc[-1]), 2)
    avg_volume_50d = float(window["Volume"].mean())
    avg_volume_10d = float(hist.tail(10)["Volume"].mean())

    return {
        "ticker": ticker,
        "name": info.get("shortName", ticker),
        "sector": info.get("sector", "Unknown"),
        "industry": info.get("industry", "Unknown"),
        "market_cap": market_cap,
        "price": price,
        "range_50d_pct": range_pct,
        "low_50d": round(low_50d, 2),
        "high_50d": round(high_50d, 2),
        "fifty_two_wk_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_wk_low": info.get("fiftyTwoWeekLow"),
        "avg_volume_50d": avg_volume_50d,
        "avg_volume_10d": avg_volume_10d,
        "business_summary": info.get("longBusinessSummary"),
        "profit_margin": info.get("profitMargins"),
        "return_on_equity": info.get("returnOnEquity"),
        "debt_to_equity": info.get("debtToEquity"),
        "revenue_growth": info.get("revenueGrowth"),
    }


def screen_universe(tickers: list[str]) -> list[dict]:
    """Screen a list of tickers, skipping any that error out or fail the criteria."""
    results = []
    for ticker in tickers:
        try:
            result = screen_ticker(ticker)
        except Exception:
            continue
        if result:
            results.append(result)
    return results


_TICKERS_FILE = os.path.join(os.path.dirname(__file__), "tickers.txt")


def _load_tickers_fallback() -> list[str]:
    with open(_TICKERS_FILE) as f:
        return [line.strip().upper() for line in f if line.strip() and not line.startswith("#")]


def fetch_universe(
    min_cap: int = MIN_MARKET_CAP,
    max_cap: int = MAX_MARKET_CAP,
    limit: int = 250,
) -> list[str]:
    """Pull fresh US small/mid-cap tickers from the Yahoo Finance screener.

    Queries the live screener for US equities in the target cap band with at
    least 100k average daily volume, sorted by today's volume so the most
    active names come first.  Falls back to tickers.txt if the screener is
    unavailable (rate-limited, API change, etc.).
    """
    try:
        import yfinance as yf
        from yfinance import EquityQuery

        q = EquityQuery("and", [
            EquityQuery("gte", ["intradaymarketcap", min_cap]),
            EquityQuery("lt",  ["intradaymarketcap", max_cap]),
            EquityQuery("eq",  ["region", "us"]),
            EquityQuery("gt",  ["avgdailyvol3m", 100_000]),
        ])
        result = yf.screen(q, size=limit, sortField="dayvolume", sortAsc=False)
        quotes = result.get("quotes", []) if isinstance(result, dict) else []
        tickers = [item["symbol"] for item in quotes if item.get("symbol")]
        if tickers:
            return tickers
        print("Screener returned no results; falling back to tickers.txt")
    except Exception as exc:
        print(f"Screener unavailable ({exc}); falling back to tickers.txt")

    return _load_tickers_fallback()


if __name__ == "__main__":
    for row in screen_universe(["AEO", "PLAY", "SMPL"]):
        print(row)
