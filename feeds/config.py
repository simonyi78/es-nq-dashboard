from __future__ import annotations

import tomllib
from pathlib import Path

_DEFAULTS = {
    "market_refresh_seconds": 5,
    "levels_refresh_seconds": 60,
    "calendar_refresh_seconds": 600,
    "earnings_refresh_seconds": 3600,
}


def load_settings() -> dict:
    path = Path(__file__).resolve().parent.parent / "dashboard.toml"
    if not path.exists():
        return dict(_DEFAULTS)
    with path.open("rb") as f:
        data = tomllib.load(f)
    return {**_DEFAULTS, **data.get("feeds", {})}
