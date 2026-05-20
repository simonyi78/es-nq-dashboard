"""Live dashboard panels — called from app.py via st.fragment."""
from __future__ import annotations

import streamlit as st

from feeds.calendar import fetch_economic_calendar
from feeds.timeutil import fmt_clock, fmt_date, now_et as eastern_now
from feeds.config import load_settings
from feeds.earnings import fetch_earnings
from feeds.levels import fetch_es_levels
from feeds.market import fetch_quotes

SETTINGS = load_settings()


def _is_stale(key: str, seconds: int) -> bool:
    last = st.session_state.get(f"_ts_{key}")
    if last is None:
        return True
    return (eastern_now() - last).total_seconds() >= seconds


def _touch(key: str) -> None:
    st.session_state[f"_ts_{key}"] = eastern_now()


def render_live_dashboard(
    *,
    fp,
    chg_html,
    imp_badge,
    minutes_to_next_high_event,
    risk_regime,
    metric_card,
    lvl_row,
    calculate_bias,
    bias_label,
    generate_trade_plan,
) -> None:
    now_et = eastern_now()

    if _is_stale("levels", SETTINGS["levels_refresh_seconds"]):
        lvls = fetch_es_levels(now_et)
        st.session_state["lvls_cache"] = lvls
        _touch("levels")
    else:
        lvls = st.session_state.get("lvls_cache") or fetch_es_levels(now_et)

    if st.session_state.get("lvl_override"):
        for key in ("pdh", "pdl", "pdc", "oh", "ol", "vwap", "poc", "vah", "val"):
            ovr = st.session_state.get(f"lvl_{key}")
            if ovr is not None:
                lvls[key] = ovr
    st.session_state["lvls_auto"] = lvls

    md, feed_ts, feed_src = fetch_quotes()
    if _is_stale("calendar", SETTINGS["calendar_refresh_seconds"]):
        st.session_state["econ_events"], st.session_state["cal_src"] = fetch_economic_calendar()
        _touch("calendar")
    if _is_stale("earnings", SETTINGS["earnings_refresh_seconds"]):
        st.session_state["earnings"] = fetch_earnings()
        _touch("earnings")

    econ_events = st.session_state.get("econ_events", [])
    earnings = st.session_state.get("earnings", [])
    cal_src = st.session_state.get("cal_src", "fallback")
    feed_et = fmt_clock(feed_ts) if feed_ts else fmt_clock(now_et)

    if hdr_time := st.session_state.get("_hdr_time"):
        hdr_time.markdown(
            f'<div style="text-align:right;padding-top:12px;">'
            f'<span style="color:#5a7099;font-size:12px;">{fmt_date(now_et)}</span><br>'
            f'<span style="color:#4fc3f7;font-family:monospace;font-size:22px;font-weight:700;">'
            f'{fmt_clock(now_et)}</span></div>',
            unsafe_allow_html=True,
        )
    src_icon = "📡" if feed_src == "rithmic" else "⚠️"
    src_label = "Rithmic paper" if feed_src == "rithmic" else "yfinance fallback"
    st.caption(
        f"🟢 Live · {src_icon} {src_label} · ES/NQ/VIX/TNX/DXY @ {feed_et} · "
        f"calendar ({cal_src}) · refresh {SETTINGS['market_refresh_seconds']}s · US/Eastern"
    )

    # ── Market overview ─────────────────────────────────────────
    st.markdown('<div class="sec-head">📈 Market Overview</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    es = md.get("ES", {})
    nq = md.get("NQ", {})
    vx = md.get("VIX", {})
    tn = md.get("TNX", {})
    dy = md.get("DXY", {})
    vx_p = vx.get("price")

    with c1:
        st.markdown(metric_card("E-Mini S&P 500 (ES)", fp(es.get("price")),
                               chg_html(es.get("change", 0), es.get("chg_pct", 0))), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("E-Mini Nasdaq 100 (NQ)", fp(nq.get("price")),
                               chg_html(nq.get("change", 0), nq.get("chg_pct", 0))), unsafe_allow_html=True)
    with c3:
        vx_col = "down" if vx_p and vx_p > 25 else ("up" if vx_p and vx_p < 15 else "flat")
        st.markdown(metric_card("CBOE VIX", f'<span class="{vx_col}">{fp(vx_p)}</span>',
                               chg_html(vx.get("change", 0), vx.get("chg_pct", 0))), unsafe_allow_html=True)
    with c4:
        tn_pc = tn.get("chg_pct", 0)
        tn_col = "down" if tn_pc > 2 else ("up" if tn_pc < -2 else "flat")
        st.markdown(metric_card("10-Year Yield (TNX)", f'<span class="{tn_col}">{fp(tn.get("price"), 3)}%</span>',
                               chg_html(tn.get("change", 0), tn_pc)), unsafe_allow_html=True)
    with c5:
        dy_pc = dy.get("chg_pct", 0)
        dy_col = "down" if dy_pc > 0.5 else ("up" if dy_pc < -0.5 else "flat")
        st.markdown(metric_card("DXY (Dollar Index)", f'<span class="{dy_col}">{fp(dy.get("price"), 3)}</span>',
                               chg_html(dy.get("change", 0), dy_pc)), unsafe_allow_html=True)
    with c6:
        regime_txt, regime_cls = risk_regime(vx_p, vx.get("chg_pct", 0))
        nq_warn = '<span class="warn">⚠ Yields spiking — NQ headwind</span>' if tn.get("chg_pct", 0) > 2 else ""
        st.markdown(metric_card("Market Regime",
                               f'<span class="badge {regime_cls}" style="font-size:14px;padding:5px 14px;">{regime_txt}</span>',
                               nq_warn or '<span class="flat">Monitoring…</span>'), unsafe_allow_html=True)

    # ── Key levels + calendar ───────────────────────────────────
    col_lvl, col_cal = st.columns([1, 1.5])
    es_p = md.get("ES", {}).get("price") or 0
    pdh, pdl, pdc = lvls["pdh"], lvls["pdl"], lvls["pdc"]
    oh, ol = lvls["oh"], lvls["ol"]
    vwap, poc, vah, val = lvls["vwap"], lvls["poc"], lvls["vah"], lvls["val"]

    with col_lvl:
        st.markdown('<div class="sec-head">📐 Key Levels — ES (auto)</div>', unsafe_allow_html=True)
        st.caption(
            f"{lvls.get('as_of', '—')} · {lvls.get('session', '')} · "
            f"prior RTH {lvls.get('prior_rth_date', '—')}"
        )
        pdh_col = "#00e676" if (pdh is not None and es_p > pdh) else "#c8d8ff"
        pdl_col = "#ff5252" if (pdl is not None and es_p < pdl) else "#c8d8ff"
        vwap_col = "#00e676" if (vwap is not None and es_p > vwap) else "#ff5252"
        body = (
            lvl_row("Prior Day High", pdh, pdh_col, "▲ ABOVE" if (pdh is not None and es_p > pdh) else "")
            + lvl_row("Prior Day Close", pdc)
            + lvl_row("Prior Day Low", pdl, pdl_col, "▼ BELOW" if (pdl is not None and es_p < pdl) else "")
            + '<div style="border-top:1px dashed #1a2744;margin:8px 2px;"></div>'
            + lvl_row("Overnight High", oh)
            + lvl_row("Overnight Low", ol)
            + '<div style="border-top:1px dashed #1a2744;margin:8px 2px;"></div>'
            + lvl_row("VWAP", vwap, vwap_col, "▲ above" if (vwap is not None and es_p > vwap) else "▼ below")
            + lvl_row("POC", poc, "#c084fc")
            + lvl_row("Value Area High", vah, "#4fc3f7")
            + lvl_row("Value Area Low", val, "#4fc3f7")
        )
        st.markdown(f'<div class="card">{body}</div>', unsafe_allow_html=True)

    with col_cal:
        st.markdown('<div class="sec-head">📅 Economic Calendar (ET)</div>', unsafe_allow_html=True)
        mins_away = minutes_to_next_high_event(now_et, econ_events)
        if mins_away is not None and mins_away < 30:
            st.markdown(
                f'<div class="no-trade-box">⛔ HIGH-IMPACT EVENT IN {mins_away:.0f} MIN — CONSIDER NO-TRADE ZONE</div>',
                unsafe_allow_html=True,
            )
        rows = ""
        for ev in econ_events:
            try:
                h, m = map(int, ev["time"].split(":"))
                ev_dt = now_et.replace(hour=h, minute=m, second=0, microsecond=0)
                is_past = ev_dt < now_et
            except Exception:
                is_past = False
            op = "0.4" if is_past else "1.0"
            past = ' <span style="color:#5a7099;font-size:10px;">(past)</span>' if is_past else ""
            rows += f"""
<div class="cal-row" style="opacity:{op};">
  <span class="cal-time">{ev['time']}</span>
  <span class="cal-name">{ev['name']}{past}</span>
  <span class="cal-prev">Prev: {ev['prev']}&nbsp;&nbsp;Exp: {ev['exp']}</span>
  {imp_badge(ev['imp'])}
</div>"""
        cal_note = "Finnhub live" if cal_src == "finnhub" else "Set FINNHUB_API_KEY for live US calendar"
        st.markdown(f'<div class="card">{rows}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#5a7099;font-size:10px;text-align:right;">{cal_note}</div>', unsafe_allow_html=True)

    # ── Earnings + bias ─────────────────────────────────────────
    col_earn, col_bias = st.columns([1.5, 1])
    score, breakdown = calculate_bias(md, lvls)
    lbl, color = bias_label(score)
    disp = f"+{score}" if score > 0 else str(score)

    with col_earn:
        st.markdown('<div class="sec-head">💰 Earnings Watch — Mega Cap</div>', unsafe_allow_html=True)
        hdr = """<div style="display:flex;gap:10px;padding:4px 10px;margin-bottom:2px;">
  <span style="color:#5a7099;font-size:9px;min-width:54px;">TICKER</span>
  <span style="color:#5a7099;font-size:9px;flex:1;">COMPANY</span>
  <span style="color:#5a7099;font-size:9px;min-width:60px;">DATE</span>
  <span style="color:#5a7099;font-size:9px;min-width:32px;">TIME</span>
  <span style="color:#5a7099;font-size:9px;min-width:54px;">EPS EST</span>
  <span style="color:#5a7099;font-size:9px;min-width:60px;">REV EST</span>
</div>"""
        rows = ""
        for e in earnings:
            tc = "earn-bmo" if e.get("timing") == "BMO" else "earn-amc"
            rows += f"""
<div class="earn-row">
  <span class="earn-tkr">{e['ticker']}</span>
  <span class="earn-co">{e['name']}</span>
  <span class="earn-dt">{e['date']}</span>
  <span class="{tc}">{e['timing']}</span>
  <span class="earn-eps">{e['eps']}</span>
  <span class="earn-rev">{e['rev']}</span>
</div>"""
        st.markdown(f'<div class="card">{hdr}{rows}</div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#5a7099;font-size:10px;text-align:right;">Yahoo Finance · refreshed hourly</div>', unsafe_allow_html=True)

    with col_bias:
        st.markdown('<div class="sec-head">🎯 Market Bias Score</div>', unsafe_allow_html=True)
        sig_rows = ""
        for icon, desc, impact in breakdown:
            ic = "#00e676" if "Bullish" in impact else ("#ff5252" if "Bearish" in impact else "#ffd740")
            sig_rows += f"""
<div class="bias-sig-row">
  <span style="color:#c8d8ff;">{icon} {desc}</span>
  <span style="color:{ic};font-weight:700;font-size:11px;min-width:80px;text-align:right;">{impact}</span>
</div>"""
        st.markdown(f"""
<div class="card">
  <div class="bias-num" style="color:{color};">{disp}</div>
  <div class="bias-lbl" style="color:{color};">{lbl}</div>
  <div style="color:#5a7099;font-size:10px;text-align:center;margin-top:4px;">−5 → +5</div>
  <div style="border-top:1px solid #1a2744;margin:14px 0 10px;"></div>
  <div style="font-size:10px;color:#5a7099;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">Signal Breakdown</div>
  {sig_rows}
</div>""", unsafe_allow_html=True)

    # ── Trade plan ──────────────────────────────────────────────
    st.divider()
    st.markdown('<div class="sec-head">📋 Trade Plan Generator</div>', unsafe_allow_html=True)
    plans = generate_trade_plan(md, lvls, score)
    tp1, tp2, tp3 = st.columns(3)
    with tp1:
        st.markdown(f"""
<div class="plan-box" style="border-left-color:#00e676;">
  <div class="plan-lbl" style="color:#00e676;">🟢 Bull Case</div>
  <div class="plan-txt">{plans['bull']}</div>
</div>
<div class="plan-box" style="border-left-color:#c084fc;">
  <div class="plan-lbl" style="color:#c084fc;">🔷 Liquidity Zones</div>
  <div class="plan-txt">{plans['liquidity']}</div>
</div>""", unsafe_allow_html=True)
    with tp2:
        st.markdown(f"""
<div class="plan-box" style="border-left-color:#ff5252;">
  <div class="plan-lbl" style="color:#ff5252;">🔴 Bear Case</div>
  <div class="plan-txt">{plans['bear']}</div>
</div>""", unsafe_allow_html=True)
    with tp3:
        st.markdown(f"""
<div class="plan-box" style="border-left-color:#ffd740;">
  <div class="plan-lbl" style="color:#ffd740;">⚠ Key Invalidation Levels</div>
  <div class="plan-txt">{plans['invalid']}</div>
</div>
<div class="plan-box" style="border-left-color:#ff8c00;">
  <div class="plan-lbl" style="color:#ff8c00;">⛔ No-Trade Conditions</div>
  <div class="plan-txt">{plans['no_trade']}</div>
</div>""", unsafe_allow_html=True)
