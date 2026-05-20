"""Economic calendar — Forex Factory JSON feed, fallback on error."""
from __future__ import annotations

import requests
from dateutil import parser as dateutil_parser

from feeds.timeutil import ET, now_et as eastern_now

_FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

_IMP_MAP = {"High": "HIGH", "Medium": "MED", "Low": "LOW"}

_FALLBACK = [
    {"time": "08:30", "name": "Initial Jobless Claims", "prev": "—", "exp": "—", "imp": "HIGH"},
    {"time": "10:00", "name": "ISM Manufacturing PMI",  "prev": "—", "exp": "—", "imp": "HIGH"},
]


def fetch_economic_calendar() -> tuple[list[dict], str]:
    today_et = eastern_now().date()
    try:
        r = requests.get(
            _FF_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return _FALLBACK, "fallback"

    events = []
    for row in data:
        if row.get("country") != "USD":
            continue
        raw_date = row.get("date", "")
        try:
            dt = dateutil_parser.parse(raw_date).astimezone(ET)
        except Exception:
            continue
        if dt.date() != today_et:
            continue
        time_str = dt.strftime("%H:%M")
        if time_str == "00:00":
            continue
        events.append({
            "time": time_str,
            "name": row.get("title") or "—",
            "prev": row.get("previous") or "—",
            "exp":  row.get("forecast") or "—",
            "imp":  _IMP_MAP.get(row.get("impact", ""), "LOW"),
        })

    events.sort(key=lambda e: e["time"])
    return (events if events else _FALLBACK), "forexfactory"
