# Claude Code — Futures Data Build

## What this project is

Streamlit morning dashboard for ES/NQ. Live quotes in `feeds/market.py`. **Key levels** in `feeds/levels.py` (not hardcoded sidebar values).

## If levels look wrong — debug checklist

1. **Confirm the bug type**
   - Old bug: sidebar used fixed defaults (`5850`, `5780`, …) — never live.
   - Fix: levels come from `fetch_es_levels()` in `feeds/levels.py`.

2. **Run the level fetch in terminal** (fastest truth test):
   ```powershell
   cd "C:\Users\Simon\Desktop\Futures Data Build"
   .\venv\Scripts\Activate.ps1
   python -c "from feeds.levels import fetch_es_levels; print(fetch_es_levels())"
   ```
   Compare PDH/PDL/PDC to your chart (RTH session prior day).

3. **Session definitions** (edit in `feeds/levels.py` if your desk differs):
   - Prior day = last **RTH** 09:30–16:00 ET
   - Overnight = **18:00** prior calendar day → 09:30 today (or now if pre-market)
   - VWAP / POC / VAH / VAL = current **overnight** before 9:30 ET, else **today RTH**

4. **Where UI reads levels**
   - Live: `ui/render.py` → `fetch_es_levels()` each fragment tick
   - Sidebar: mirror from `st.session_state.lvls_auto` (main panel is authoritative)

5. **Only edit these files for level logic**
   - `feeds/levels.py` — calculations
   - `ui/render.py` — display
   - `app.py` — sidebar override only

6. **Do not** paste `venv/` or refetch per symbol in loops.

## Run dashboard

```powershell
cd "C:\Users\Simon\Desktop\Futures Data Build"
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

## Tune refresh

`dashboard.toml` → `[feeds] market_refresh_seconds`

## Optional calendar API

```powershell
$env:FINNHUB_API_KEY = "your_key"
```
