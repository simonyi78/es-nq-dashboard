# ============================================================
#  ES / NQ  FUTURES  MORNING  DASHBOARD
#  Streamlit · Rithmic paper trading · dark trading theme
# ============================================================
import streamlit as st
from datetime import datetime

from feeds.config import load_settings
from feeds.levels import fetch_es_levels
from feeds.timeutil import fmt_clock, fmt_date, now_et as eastern_now
from ui.render import render_live_dashboard

SETTINGS = load_settings()

# ── must be first Streamlit call ──────────────────────────────
st.set_page_config(
    page_title="ES/NQ Morning Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
#  DARK TRADING CSS
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── base ── */
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
html, body { background-color: #0b0f1e !important; }
.stApp { background-color: #0b0f1e !important; }
[data-testid="stSidebar"] {
    background-color: #0d1220 !important;
    border-right: 1px solid #1a2744;
}
#MainMenu, footer, header { visibility: hidden; }
hr { border-color: #1a2744 !important; margin: 10px 0 !important; }

/* ── suppress fragment loading flash ── */
[data-stale] { opacity: 1 !important; transition: none !important; }
.stStatusWidget { display: none !important; }
iframe[title="st_bridge.streamlit_bridge"] { display: none !important; }

/* ── section header ── */
.sec-head {
    font-size: 11px; font-weight: 700; color: #4fc3f7;
    text-transform: uppercase; letter-spacing: 2.5px;
    border-bottom: 1px solid #1a2744;
    padding-bottom: 8px; margin-bottom: 14px;
}

/* ── card ── */
.card {
    background: linear-gradient(145deg,#111827,#141d30);
    border: 1px solid #1e3460; border-radius: 10px;
    padding: 16px 18px; margin-bottom: 10px;
}

/* ── metric card ── */
.mc-label {
    font-size: 10px; font-weight: 600; color: #5a7099;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px;
}
.mc-value {
    font-size: 28px; font-weight: 800; color: #c8d8ff;
    font-family: 'Courier New', monospace; line-height: 1.05;
}
.mc-sub { font-size: 12px; margin-top: 3px; }

/* ── colour tokens ── */
.up   { color: #00e676; } .down { color: #ff5252; }
.flat { color: #78909c; } .warn { color: #ffd740; }

/* ── badges ── */
.badge {
    display: inline-block; padding: 3px 11px; border-radius: 20px;
    font-size: 10px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1px;
}
.b-bull   { background:#00e67612; color:#00e676; border:1px solid #00e67645; }
.b-bear   { background:#ff525212; color:#ff5252; border:1px solid #ff525245; }
.b-neut   { background:#ffd74012; color:#ffd740; border:1px solid #ffd74045; }
.b-warn   { background:#ff8c0012; color:#ff8c00; border:1px solid #ff8c0045; }

/* ── key-level row ── */
.lvl-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 10px; border-radius: 6px; margin: 3px 0;
    background: #0f1624; border: 1px solid #1a2744; font-size: 12px;
}
.lvl-lbl { color: #5a7099; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
.lvl-val { font-family: 'Courier New', monospace; font-weight: 700; font-size: 14px; }

/* ── calendar ── */
.cal-row {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 10px; border-radius: 6px; margin: 4px 0;
    background: #0f1624; border: 1px solid #1a2744; font-size: 12px;
}
.cal-time { color: #4fc3f7; font-family: monospace; min-width: 52px; }
.cal-name { color: #c8d8ff; flex: 1; }
.cal-prev { color: #5a7099; font-size: 11px; min-width: 110px; text-align: right; }
.imp-hi  { color: #ff5252; font-size: 10px; font-weight: 700; min-width: 32px; }
.imp-med { color: #ffd740; font-size: 10px; font-weight: 700; min-width: 32px; }
.imp-lo  { color: #5a7099; font-size: 10px; font-weight: 700; min-width: 32px; }

/* ── earnings ── */
.earn-row {
    display: flex; align-items: center; gap: 10px;
    padding: 8px 10px; border-radius: 6px; margin: 4px 0;
    background: #0f1624; border: 1px solid #1a2744; font-size: 12px;
}
.earn-tkr { color: #4fc3f7; font-weight: 800; font-family: monospace; min-width: 54px; font-size:13px; }
.earn-co  { color: #8899bb; flex: 1; }
.earn-dt  { color: #c8d8ff; min-width: 60px; }
.earn-bmo { color: #00e676; font-size: 10px; font-weight: 700; min-width: 32px; }
.earn-amc { color: #4fc3f7; font-size: 10px; font-weight: 700; min-width: 32px; }
.earn-eps { color: #c8d8ff; font-family: monospace; min-width: 54px; }
.earn-rev { color: #8899bb; min-width: 60px; }

/* ── bias score ── */
.bias-num  { font-size: 60px; font-weight: 900; font-family: 'Courier New', monospace; text-align:center; line-height:1; }
.bias-lbl  { font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 3px; text-align:center; margin-top:6px; }
.bias-sig-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 5px 0; border-bottom: 1px solid #131c2e; font-size: 12px;
}

/* ── trade plan ── */
.plan-box {
    border-radius: 8px; padding: 14px 16px; margin: 6px 0;
    border-left: 4px solid; background: #0f1624;
}
.plan-lbl { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }
.plan-txt { color: #c8d8ff; font-size: 13px; line-height: 1.65; }

/* ── no-trade flash ── */
.no-trade-box {
    background: #ff17440d; border: 1px solid #ff5252;
    border-radius: 8px; padding: 12px; text-align: center;
    color: #ff5252; font-weight: 700; font-size: 13px; letter-spacing: 1.5px;
    margin-bottom: 10px;
}

/* ── sidebar inputs ── */
[data-testid="stNumberInput"] input {
    background: #0f1624 !important; color: #c8d8ff !important;
    border-color: #1e3460 !important;
}
[data-testid="stSidebar"] label { color: #8899bb !important; font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════
def fp(v, d=2) -> str:
    """Format price — returns em-dash if None."""
    return f"{v:,.{d}f}" if v is not None else "—"

def chg_html(chg: float, pct: float) -> str:
    arrow = "▲" if chg >= 0 else "▼"
    cls   = "up" if chg >= 0 else "down"
    return f'<span class="{cls}">{arrow} {abs(chg):,.3f} ({abs(pct):.2f}%)</span>'

def imp_badge(imp: str) -> str:
    if imp == "HIGH":  return '<span class="imp-hi">HIGH</span>'
    if imp == "MED":   return '<span class="imp-med">MED</span>'
    return '<span class="imp-lo">LOW</span>'

def minutes_to_next_high_event(now_et: datetime, events: list) -> float | None:
    """Return fractional minutes until next HIGH-impact event, or None."""
    mins = []
    for ev in events:
        if ev["imp"] != "HIGH":
            continue
        try:
            h, m  = map(int, ev["time"].split(":"))
            ev_dt = now_et.replace(hour=h, minute=m, second=0, microsecond=0)
            diff  = (ev_dt - now_et).total_seconds() / 60
            if 0 < diff <= 60:
                mins.append(diff)
        except Exception:
            pass
    return min(mins) if mins else None

def risk_regime(vix_price, vix_pct) -> tuple[str, str]:
    if vix_price is None:
        return "UNKNOWN", "b-neut"
    if vix_price > 25 or vix_pct > 5:
        return "RISK-OFF", "b-bear"
    if vix_price < 15 and vix_pct < 0:
        return "RISK-ON", "b-bull"
    return "NEUTRAL", "b-neut"

def metric_card(label: str, value: str, sub: str = "", extra: str = "") -> str:
    return f"""
<div class="card">
  <div class="mc-label">{label}</div>
  <div class="mc-value">{value}</div>
  <div class="mc-sub">{sub}</div>
  {f'<div style="margin-top:8px;">{extra}</div>' if extra else ""}
</div>"""

def lvl_row(label: str, value: float, color: str = "#c8d8ff", tag: str = "") -> str:
    tag_html = f'<span style="font-size:9px;color:{color};margin-left:6px;font-weight:700;">{tag}</span>' if tag else ""
    return f"""
<div class="lvl-row">
  <span class="lvl-lbl">{label}</span>
  <span class="lvl-val" style="color:{color};">{fp(value)}{tag_html}</span>
</div>"""


# ═══════════════════════════════════════════════════════════════
#  BIAS SCORE
# ═══════════════════════════════════════════════════════════════
def calculate_bias(md: dict, lvls: dict) -> tuple[int, list]:
    score = 0
    breakdown = []

    es_p   = md.get("ES",  {}).get("price")
    vix_p  = md.get("VIX", {}).get("price")
    vix_pc = md.get("VIX", {}).get("chg_pct", 0)
    tnx_pc = md.get("TNX", {}).get("chg_pct", 0)
    dxy_pc = md.get("DXY", {}).get("chg_pct", 0)

    vwap = lvls.get("vwap")
    pdh  = lvls.get("pdh")
    pdl  = lvls.get("pdl")

    def add(pts, icon, desc, impact_str):
        nonlocal score
        score += pts
        breakdown.append((icon, desc, impact_str))

    # 1. Price vs VWAP
    if es_p and vwap:
        if es_p > vwap:
            add(+1, "✅", f"ES ({fp(es_p)}) above VWAP ({fp(vwap)})", "+1 Bullish")
        else:
            add(-1, "🔴", f"ES ({fp(es_p)}) below VWAP ({fp(vwap)})", "−1 Bearish")

    # 2. Price vs Prior Day High/Low
    if es_p and pdh:
        if es_p > pdh:
            add(+1, "✅", f"ES above Prior Day High ({fp(pdh)})", "+1 Bullish")
        else:
            breakdown.append(("🟡", f"ES below PDH ({fp(pdh)}) — resistance", "0"))
    if es_p and pdl:
        if es_p < pdl:
            add(-1, "🔴", f"ES below Prior Day Low ({fp(pdl)})", "−1 Bearish")

    # 3. VIX level
    if vix_p is not None:
        if vix_p > 25:
            add(-1, "🔴", f"VIX elevated at {fp(vix_p)}", "−1 Bearish")
        elif vix_p < 15:
            add(+1, "✅", f"VIX suppressed at {fp(vix_p)}", "+1 Bullish")
        else:
            breakdown.append(("🟡", f"VIX neutral at {fp(vix_p)}", "0"))

    # 4. VIX direction
    if vix_pc > 5:
        add(-1, "🔴", f"VIX spiking (+{vix_pc:.1f}%)", "−1 Bearish")
    elif vix_pc < -3:
        add(+1, "✅", f"VIX falling ({vix_pc:.1f}%)", "+1 Bullish")

    # 5. 10Y yield direction (sharp moves hurt NQ)
    if tnx_pc > 2:
        add(-1, "🔴", f"10Y yield rising sharply (+{tnx_pc:.1f}%)", "−1 Bearish NQ")
    elif tnx_pc < -2:
        add(+1, "✅", f"10Y yield falling ({tnx_pc:.1f}%)", "+1 Bullish NQ")

    # 6. DXY direction
    if dxy_pc > 0.5:
        add(-1, "🔴", f"DXY rising (+{dxy_pc:.2f}%)", "−1 Bearish")
    elif dxy_pc < -0.5:
        add(+1, "✅", f"DXY falling ({dxy_pc:.2f}%)", "+1 Bullish")

    return max(-5, min(5, score)), breakdown

def bias_label(score: int) -> tuple[str, str]:
    if score >= 3:    return "STRONGLY BULLISH", "#00e676"
    if score >= 1:    return "BULLISH",           "#40c057"
    if score == 0:    return "NEUTRAL",            "#ffd740"
    if score >= -2:   return "BEARISH",            "#ff6b6b"
    return "STRONGLY BEARISH", "#ff1744"


# ═══════════════════════════════════════════════════════════════
#  TRADE PLAN GENERATOR
# ═══════════════════════════════════════════════════════════════
def generate_trade_plan(md: dict, lvls: dict, score: int) -> dict:
    f = lambda v: fp(v) if v else "—"

    vwap = lvls.get("vwap", 0)
    pdh  = lvls.get("pdh",  0)
    pdl  = lvls.get("pdl",  0)
    pdc  = lvls.get("pdc",  0)
    oh   = lvls.get("oh",   0)
    ol   = lvls.get("ol",   0)
    poc  = lvls.get("poc",  0)
    vah  = lvls.get("vah",  0)
    val  = lvls.get("val",  0)

    bull = f"""
<b>Entry:</b> Pullbacks to VWAP ({f(vwap)}) or VAH ({f(vah)}) while holding above POC.<br>
<b>Target 1:</b> Prior Day High {f(pdh)} — breakout trigger.<br>
<b>Target 2:</b> Measured move above PDH on high-volume expansion.<br>
<b>Confirmation:</b> 5-min closes above VWAP with VIX holding flat or declining.<br>
<b>Thesis:</b> Buyers defending VWAP; any dip is an opportunity while structure holds.
"""
    # Bear targets: only levels strictly below VWAP, nearest first
    _bear_cands = [("POC", poc), ("Value Area Low", val), ("Prior Day Low", pdl), ("Overnight Low", ol)]
    _bear_tgts = sorted(
        [(n, v) for n, v in _bear_cands if v and vwap and v < vwap],
        key=lambda x: x[1], reverse=True,
    )
    _bt1 = f"<b>Target 1:</b> {_bear_tgts[0][0]} ({f(_bear_tgts[0][1])}) — first flush target.<br>" if _bear_tgts else "<b>Target 1:</b> Below entry.<br>"
    _bt2 = f"<b>Target 2:</b> {_bear_tgts[1][0]} ({f(_bear_tgts[1][1])}) — full bear extension.<br>" if len(_bear_tgts) > 1 else ""

    bear = f"""
<b>Entry:</b> Failed retests of VWAP ({f(vwap)}) or PDClose ({f(pdc)}).<br>
{_bt1}{_bt2}<b>Confirmation:</b> Rejection at POC ({f(poc)}) with VIX expanding, DXY bid.<br>
<b>Thesis:</b> Sellers defending VWAP; failed auction targets PDL stop-run.
"""
    invalid = f"""
<b>Bull case invalid if:</b> ES prints a 5-min close <b>below PDL {f(pdl)}</b> — exit longs.<br>
<b>Bear case invalid if:</b> ES recaptures VWAP ({f(vwap)}) <b>and</b> POC ({f(poc)}) on volume — cover.<br>
<b>Overnight range:</b> High {f(oh)} / Low {f(ol)} — breaks of the OR are significant.<br>
<b>Key pivot:</b> POC {f(poc)} — watch for absorption vs distribution here.
"""
    no_trade = """
<b>Avoid trading when:</b><br>
• Within 30 min of HIGH-impact economic data (dashboard flags this automatically)<br>
• First 5 minutes of RTH open (9:30–9:35 ET) unless momentum is extreme<br>
• VIX above 30 — stops need widening beyond standard risk<br>
• Spread widens abnormally (low-liquidity conditions)<br>
• No clear auction direction — wait for the market to show its hand
"""
    liquidity = f"""
<b>Stop-run targets above:</b> PDH {f(pdh)}, Overnight High {f(oh)}<br>
<b>Stop-run targets below:</b> PDL {f(pdl)}, Overnight Low {f(ol)}<br>
<b>Institutional anchors:</b> VWAP {f(vwap)}, POC {f(poc)}<br>
<b>Value area edges:</b> VAH {f(vah)} (potential fade) / VAL {f(val)} (potential fade)<br>
<b>Note:</b> Large players use these levels — expect reactions or liquidity grabs.
"""
    return {
        "bull": bull, "bear": bear,
        "invalid": invalid, "no_trade": no_trade, "liquidity": liquidity,
    }


# ═══════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════
if "lvls_auto" not in st.session_state:
    st.session_state.lvls_auto = fetch_es_levels(eastern_now())


@st.fragment(run_every=5)
def _sidebar_clock():
    st.markdown(
        f'<div style="color:#5a7099;font-size:10px;text-align:center;margin-top:6px;">'
        f'Clock: {fmt_clock(eastern_now())}</div>',
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown("### ⚙️ Key Levels — ES")
    st.caption("Auto-calculated · updates in main panel")

    override = st.checkbox("Manual override", False, key="lvl_override")
    auto = st.session_state.lvls_auto

    def _lvl_input(label: str, key: str) -> float | None:
        default = float(auto[key]) if auto.get(key) is not None else 0.0
        return st.number_input(label, value=default, step=0.25, format="%.2f", key=f"lvl_{key}")

    if override:
        st.markdown("**Prior Day (RTH)**")
        _lvl_input("Prior Day High", "pdh")
        _lvl_input("Prior Day Low", "pdl")
        _lvl_input("Prior Day Close", "pdc")
        st.markdown("**Overnight**")
        _lvl_input("Overnight High", "oh")
        _lvl_input("Overnight Low", "ol")
        st.markdown("**Volume profile**")
        _lvl_input("VWAP", "vwap")
        _lvl_input("POC", "poc")
        _lvl_input("Value Area High", "vah")
        _lvl_input("Value Area Low", "val")
    else:
        for lbl, key in [
            ("PDH", "pdh"), ("PDL", "pdl"), ("PDC", "pdc"),
            ("ONH", "oh"), ("ONL", "ol"),
            ("VWAP", "vwap"), ("POC", "poc"), ("VAH", "vah"), ("VAL", "val"),
        ]:
            v = auto.get(key)
            st.markdown(f"**{lbl}** {v:,.2f}" if v is not None else f"**{lbl}** —")
        st.caption(f"{auto.get('as_of', '')} · {auto.get('session', '')}")

    st.divider()

    live_stream = st.toggle(
        "📡 Live stream",
        value=True,
        help=f"Refreshes quotes every {SETTINGS['market_refresh_seconds']}s",
    )
    st.caption(f"Interval: {SETTINGS['market_refresh_seconds']}s · Rithmic paper / yfinance fallback")

    _sidebar_clock()

hcol1, hcol2 = st.columns([3, 1])
with hcol1:
    st.markdown("## 📊 &nbsp;ES / NQ &nbsp;Morning Dashboard")
with hcol2:
    st.session_state["_hdr_time"] = st.empty()
st.divider()

_ctx = dict(
    fp=fp, chg_html=chg_html, imp_badge=imp_badge,
    minutes_to_next_high_event=minutes_to_next_high_event,
    risk_regime=risk_regime, metric_card=metric_card, lvl_row=lvl_row,
    calculate_bias=calculate_bias, bias_label=bias_label,
    generate_trade_plan=generate_trade_plan,
)
_interval = SETTINGS["market_refresh_seconds"] if live_stream else None

@st.fragment(run_every=_interval)
def _live_panel():
    render_live_dashboard(**_ctx)

# Prime clocks before first fragment tick
_now = eastern_now()
if slot := st.session_state.get("_hdr_time"):
    slot.markdown(
        f'<div style="text-align:right;padding-top:12px;">'
        f'<span style="color:#5a7099;font-size:12px;">{fmt_date(_now)}</span><br>'
        f'<span style="color:#4fc3f7;font-family:monospace;font-size:22px;font-weight:700;">'
        f'{fmt_clock(_now)}</span></div>',
        unsafe_allow_html=True,
    )
_live_panel()

st.divider()
st.markdown(
    '<div style="color:#5a7099;font-size:11px;">'
    'Quotes: Rithmic paper trading (bridge @ localhost:8080) · yfinance fallback when offline. '
    'Levels: RTH 9:30–16:00 ET, overnight 18:00–9:30. '
    'Calendar: set FINNHUB_API_KEY for live US data.</div>',
    unsafe_allow_html=True,
)
