"""
ES key levels from Yahoo 1m bars — RTH prior day, overnight, VWAP, volume profile.

Sessions (US/Eastern, CME equity index futures):
  RTH  09:30 – 16:00
  ETH  18:00 – 09:30 (overnight into next RTH open)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta

import pandas as pd
import yfinance as yf

from feeds.timeutil import ET, fmt_stamp, now_et as eastern_now, to_et
ES_SYM = "ES=F"
TICK = 0.25

RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)
ETH_OPEN = time(18, 0)

_EMPTY = {
    "pdh": None, "pdl": None, "pdc": None,
    "oh": None, "ol": None,
    "vwap": None, "poc": None, "vah": None, "val": None,
    "as_of": None, "session": "",
}


def _flatten(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] for c in df.columns]
    return df


def _to_et(df: pd.DataFrame) -> pd.DataFrame:
    df = _flatten(df)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(ET)
    return df


def _prev_weekday(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _prior_rth_date(now_et: datetime) -> date:
    """Last completed RTH session (cash hours) date."""
    d = now_et.date()
    if now_et.weekday() == 0:  # Monday
        if now_et.time() < RTH_OPEN:
            return d - timedelta(days=3)  # Friday
        return d - timedelta(days=3)  # Monday RTH → prior is Friday
    cand = d - timedelta(days=1)
    while cand.weekday() >= 5:
        cand -= timedelta(days=1)
    if now_et.time() < RTH_OPEN and cand == d - timedelta(days=1):
        # e.g. Tue 8am → prior RTH was Mon; cand is Mon ✓
        pass
    return cand


def _overnight_window(now_et: datetime) -> tuple[datetime, datetime]:
    """ETH overnight segment ending at today's RTH open (or now if pre-RTH)."""
    if now_et.time() >= RTH_OPEN:
        end = ET.localize(datetime.combine(now_et.date(), RTH_OPEN))
    else:
        end = now_et
    start_day = end.date() - timedelta(days=1)  # Mon 9:30 → Sun 18:00
    start = ET.localize(datetime.combine(start_day, ETH_OPEN))
    return start, end


def _mask_rth(df: pd.DataFrame, day: date) -> pd.DataFrame:
    day_df = df[df.index.date == day]
    t = day_df.index.time
    return day_df[(t >= RTH_OPEN) & (t < RTH_CLOSE)]


def _mask_window(df: pd.DataFrame, start: datetime, end: datetime) -> pd.DataFrame:
    return df[(df.index >= start) & (df.index <= end)]


def _hlc(bars: pd.DataFrame) -> tuple[float | None, float | None, float | None]:
    if bars.empty:
        return None, None, None
    return (
        round(float(bars["High"].max()), 2),
        round(float(bars["Low"].min()), 2),
        round(float(bars["Close"].iloc[-1]), 2),
    )


def _vwap(bars: pd.DataFrame) -> float | None:
    if bars.empty or bars["Volume"].sum() <= 0:
        return None
    tp = (bars["High"] + bars["Low"] + bars["Close"]) / 3.0
    v = bars["Volume"].astype(float)
    return round(float((tp * v).sum() / v.sum()), 2)


def _volume_profile(bars: pd.DataFrame, pct: float = 0.70) -> tuple[float | None, float | None, float | None]:
    """POC and value area (pct of volume) using tick-sized bins."""
    if bars.empty or bars["Volume"].sum() <= 0:
        return None, None, None

    vol_at: dict[float, float] = defaultdict(float)
    for _, row in bars.iterrows():
        if row["Volume"] <= 0:
            continue
        lo = round(row["Low"] / TICK) * TICK
        hi = round(row["High"] / TICK) * TICK
        steps = max(1, int((hi - lo) / TICK) + 1)
        share = float(row["Volume"]) / steps
        p = lo
        for _ in range(steps):
            vol_at[p] += share
            p = round(p + TICK, 2)

    if not vol_at:
        return None, None, None

    poc = max(vol_at, key=vol_at.get)
    total = sum(vol_at.values())
    target = total * pct

    prices = sorted(vol_at.keys())
    poc_i = prices.index(poc)
    lo_i = hi_i = poc_i
    captured = vol_at[poc]

    while captured < target and (lo_i > 0 or hi_i < len(prices) - 1):
        vol_below = vol_at[prices[lo_i - 1]] if lo_i > 0 else -1.0
        vol_above = vol_at[prices[hi_i + 1]] if hi_i < len(prices) - 1 else -1.0
        if vol_below >= vol_above and lo_i > 0:
            lo_i -= 1
            captured += vol_at[prices[lo_i]]
        elif hi_i < len(prices) - 1:
            hi_i += 1
            captured += vol_at[prices[hi_i]]
        else:
            lo_i -= 1
            captured += vol_at[prices[lo_i]]

    return round(poc, 2), round(prices[hi_i], 2), round(prices[lo_i], 2)


def fetch_es_levels(now: datetime | None = None) -> dict:
    ts = to_et(now) if now else eastern_now()

    try:
        raw = yf.download(ES_SYM, period="5d", interval="1m", progress=False, auto_adjust=True)
        if raw is None or raw.empty:
            return {**_EMPTY, "as_of": fmt_stamp(ts)}
        df = _to_et(raw)
    except Exception:
        return {**_EMPTY, "as_of": fmt_stamp(ts)}

    prior_day = _prior_rth_date(ts)
    rth_bars = _mask_rth(df, prior_day)
    pdh, pdl, pdc = _hlc(rth_bars)

    on_start, on_end = _overnight_window(ts)
    on_bars = _mask_window(df, on_start, on_end)
    oh, ol, _ = _hlc(on_bars)

    # Developing session for VWAP / profile
    if ts.time() < RTH_OPEN:
        sess_bars = on_bars
        session = "overnight (ETH)"
    else:
        rth_start = ET.localize(datetime.combine(ts.date(), RTH_OPEN))
        sess_bars = _mask_window(df, rth_start, ts)
        session = "RTH (today)"

    vwap = _vwap(sess_bars)
    poc, vah, val = _volume_profile(sess_bars)

    return {
        "pdh": pdh, "pdl": pdl, "pdc": pdc,
        "oh": oh, "ol": ol,
        "vwap": vwap, "poc": poc, "vah": vah, "val": val,
        "as_of": fmt_stamp(ts),
        "session": session,
        "prior_rth_date": str(prior_day),
    }
