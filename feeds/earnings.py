"""Live mega-cap earnings from Yahoo Finance."""
from __future__ import annotations

from datetime import datetime

import yfinance as yf

EARNINGS_TICKERS = ["NVDA", "AAPL", "MSFT", "AMZN", "META", "TSLA", "GOOGL"]

_FALLBACK = [
    {"ticker": t, "name": t, "date": "—", "timing": "—", "eps": "—", "rev": "—"}
    for t in EARNINGS_TICKERS
]


def _fmt_date(val) -> str:
    if val is None:
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%b %d")
    return str(val)[:10]


def fetch_earnings() -> list[dict]:
    rows: list[dict] = []
    tickers = yf.Tickers(" ".join(EARNINGS_TICKERS))

    for sym in EARNINGS_TICKERS:
        try:
            t = tickers.tickers[sym]
            info = t.info or {}
            cal = t.calendar
            name = info.get("shortName") or info.get("longName") or sym

            eps = rev = date_str = timing = "—"
            if cal is not None:
                if hasattr(cal, "to_dict"):
                    cd = cal.to_dict()
                elif isinstance(cal, dict):
                    cd = cal
                else:
                    cd = {}
                if "Earnings Date" in cd:
                    ed = cd["Earnings Date"]
                    date_str = _fmt_date(ed[0] if isinstance(ed, (list, tuple)) else ed)
                if "Earnings Average" in cd:
                    eps = f"${cd['Earnings Average']:.2f}"
                if "Revenue Average" in cd:
                    rev = f"${cd['Revenue Average']/1e9:.1f}B"

            rows.append({
                "ticker": sym,
                "name": name,
                "date": date_str,
                "timing": timing,
                "eps": eps,
                "rev": rev,
            })
        except Exception:
            rows.append({"ticker": sym, "name": sym, "date": "—", "timing": "—", "eps": "—", "rev": "—"})

    return rows if rows else _FALLBACK
