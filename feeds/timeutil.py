"""US/Eastern clock — all session logic and display use this module."""
from __future__ import annotations

from datetime import datetime

import pytz

ET = pytz.timezone("US/Eastern")


def now_et() -> datetime:
    """Current wall-clock time in US/Eastern (EST or EDT per DST)."""
    return datetime.now(ET)


def to_et(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return ET.localize(dt)
    return dt.astimezone(ET)


def fmt_clock(dt: datetime | None = None) -> str:
    """e.g. 00:05:12 EDT"""
    dt = to_et(dt) if dt else now_et()
    return dt.strftime("%H:%M:%S %Z")


def fmt_date(dt: datetime | None = None) -> str:
    """e.g. Monday, May 18 2026"""
    dt = to_et(dt) if dt else now_et()
    return dt.strftime("%A, %B %d %Y")


def fmt_stamp(dt: datetime | None = None) -> str:
    """Full Eastern timestamp for level feeds."""
    dt = to_et(dt) if dt else now_et()
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


# Alias used across feeds/
eastern_now = now_et
