"""
Rithmic paper-trading bridge consumer.

Reads from the local bridge service at http://localhost:<port>/quotes.
Expected response schema:
  {
    "ES":  {"price": 5900.25, "bid": 5900.00, "ask": 5900.50, "change": 12.5, "chg_pct": 0.21},
    "NQ":  {"price": 20100.0, ...},
    "VIX": {"price": 18.4, ...},
    "TNX": {"price": 4.32, ...},
    "DXY": {"price": 104.1, ...}
  }
Optional /health endpoint:
  {"status": "ok", "connected": true, "account": "paper"}
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "rithmic.json"
_TIMEOUT = 2.0  # seconds — keep well under the fragment interval


def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with _CONFIG_PATH.open() as f:
            return json.load(f)
    return {"port": int(os.environ.get("RITHMIC_BRIDGE_PORT", 8080))}


def bridge_url() -> str:
    cfg = _load_config()
    port = cfg.get("port", 8080)
    return f"http://localhost:{port}"


def is_bridge_alive() -> bool:
    try:
        r = requests.get(f"{bridge_url()}/health", timeout=_TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def fetch_rithmic_quotes() -> dict | None:
    """Return quote dict keyed by symbol, or None if bridge is unreachable."""
    try:
        r = requests.get(f"{bridge_url()}/quotes", timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None
