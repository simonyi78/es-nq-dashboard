"""
Live quotes — Rithmic paper-trading bridge (primary) with yfinance fallback.

Source selection:
  1. Rithmic bridge at localhost:<port>/quotes  →  sub-second, paper account
  2. yfinance 1m bars                           →  fallback when bridge is down
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import yfinance as yf

from feeds.rithmic import fetch_rithmic_quotes, is_bridge_alive
from feeds.timeutil import now_et as eastern_now

SYMBOLS: dict[str, str] = {
    "ES": "ES=F",
    "NQ": "NQ=F",
    "VIX": "^VIX",
    "TNX": "^TNX",
    "DXY": "DX-Y.NYB",
}

_EMPTY = {"price": None, "change": 0.0, "chg_pct": 0.0, "prev": None}


# ── yfinance fallback ─────────────────────────────────────────────────────────

def _last_close(frame: pd.DataFrame, sym: str) -> float | None:
    if frame is None or frame.empty:
        return None
    if isinstance(frame.columns, pd.MultiIndex):
        if sym not in frame.columns.get_level_values(0):
            return None
        s = frame[sym]["Close"].dropna()
    else:
        s = frame["Close"].dropna()
    return float(s.iloc[-1]) if len(s) else None


def _prior_close(frame: pd.DataFrame, sym: str) -> float | None:
    if frame is None or frame.empty:
        return None
    if isinstance(frame.columns, pd.MultiIndex):
        if sym not in frame.columns.get_level_values(0):
            return None
        s = frame[sym]["Close"].dropna()
    else:
        s = frame["Close"].dropna()
    if len(s) >= 2:
        return float(s.iloc[-2])
    return float(s.iloc[-1]) if len(s) else None


def _yfinance_quotes() -> dict:
    syms = list(SYMBOLS.values())
    out = {k: dict(_EMPTY) for k in SYMBOLS}
    try:
        intra = yf.download(
            syms, period="1d", interval="1m",
            group_by="ticker", auto_adjust=True, progress=False, threads=True,
        )
        daily = yf.download(
            syms, period="5d", interval="1d",
            group_by="ticker", auto_adjust=True, progress=False, threads=True,
        )
    except Exception:
        return out
    for name, sym in SYMBOLS.items():
        price = _last_close(intra, sym)
        prev = _prior_close(daily, sym)
        if price is None:
            continue
        chg = (price - prev) if prev else 0.0
        chg_pct = (chg / prev * 100) if prev else 0.0
        out[name] = {
            "price": round(price, 3),
            "change": round(chg, 3),
            "chg_pct": round(chg_pct, 3),
            "prev": round(prev, 3) if prev else None,
        }
    return out


# ── normalise Rithmic payload to internal schema ──────────────────────────────

def _normalise_rithmic(raw: dict) -> dict:
    out = {k: dict(_EMPTY) for k in SYMBOLS}
    for name in SYMBOLS:
        src = raw.get(name, {})
        price = src.get("price")
        if price is None:
            continue
        chg = float(src.get("change", 0.0))
        chg_pct = float(src.get("chg_pct", 0.0))
        prev = src.get("prev") or (round(price - chg, 3) if chg else None)
        out[name] = {
            "price": round(float(price), 3),
            "change": round(chg, 3),
            "chg_pct": round(chg_pct, 3),
            "prev": round(float(prev), 3) if prev else None,
        }
    return out


# ── public API ────────────────────────────────────────────────────────────────

def fetch_quotes() -> tuple[dict, datetime, str]:
    """
    Returns (quotes_dict, timestamp, source_label).
    source_label is 'rithmic' or 'yfinance'.
    """
    ts = eastern_now()

    rithmic_data = fetch_rithmic_quotes()
    if rithmic_data is not None:
        return _normalise_rithmic(rithmic_data), ts, "rithmic"

    return _yfinance_quotes(), ts, "yfinance"
