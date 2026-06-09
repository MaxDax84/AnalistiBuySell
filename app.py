"""
Analisti BuySell — Streamlit app
Confronta il consenso degli analisti da Yahoo Finance e Finnhub.
"""

import re
import streamlit as st
import yfinance as yf
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any

# ─── CSS Futuristico ──────────────────────────────────────────────────────────

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

.stApp {
    background: radial-gradient(ellipse at 20% 20%, #0d1535 0%, #07090f 60%) !important;
    background-attachment: fixed !important;
}
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(0,212,255,.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,.04) 1px, transparent 1px);
    background-size: 44px 44px;
    pointer-events: none;
    z-index: 0;
}
h1 {
    font-family: 'Orbitron', monospace !important;
    font-weight: 900 !important;
    font-size: 2.4rem !important;
    letter-spacing: .12em !important;
    background: linear-gradient(90deg, #00d4ff 0%, #a855f7 50%, #00d4ff 100%);
    background-size: 200% auto;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    animation: holo-shift 4s linear infinite;
    filter: drop-shadow(0 0 12px rgba(0,212,255,.45));
}
h2 {
    font-family: 'Orbitron', monospace !important;
    font-weight: 700 !important;
    letter-spacing: .08em !important;
    color: #00d4ff !important;
    text-shadow: 0 0 14px rgba(0,212,255,.55), 0 0 2px #fff;
}
h3 {
    font-family: 'Orbitron', monospace !important;
    font-weight: 400 !important;
    color: #a855f7 !important;
    text-shadow: 0 0 10px rgba(168,85,247,.5);
    letter-spacing: .06em !important;
}
@keyframes holo-shift {
    0%   { background-position: 0%   center; }
    100% { background-position: 200% center; }
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #08101f 0%, #060c1a 100%) !important;
    border-right: 1px solid rgba(0,212,255,.18) !important;
    box-shadow: 4px 0 24px rgba(0,212,255,.07) !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { font-size: 1rem !important; }
.stButton > button[kind="primary"] {
    font-family: 'Orbitron', monospace !important;
    font-size: .7rem !important;
    letter-spacing: .15em !important;
    text-transform: uppercase !important;
    background: linear-gradient(135deg, rgba(168,85,247,.15), rgba(0,212,255,.1)) !important;
    border: 1px solid #a855f7 !important;
    color: #c084fc !important;
    transition: all .3s !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, rgba(168,85,247,.3), rgba(0,212,255,.2)) !important;
    box-shadow: 0 0 20px rgba(168,85,247,.5), 0 0 40px rgba(0,212,255,.15) !important;
    transform: translateY(-1px) !important;
    border-color: #c084fc !important;
}
.stButton > button {
    font-family: 'Share Tech Mono', monospace !important;
    font-size: .75rem !important;
    letter-spacing: .08em !important;
    background: transparent !important;
    border: 1px solid rgba(0,212,255,.35) !important;
    color: #67e8f9 !important;
    transition: all .25s !important;
}
.stButton > button:hover {
    background: rgba(0,212,255,.08) !important;
    box-shadow: 0 0 12px rgba(0,212,255,.3) !important;
    border-color: #00d4ff !important;
}
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: rgba(0,212,255,.04) !important;
    border: 1px solid rgba(0,212,255,.25) !important;
    color: #c8e8ff !important;
    font-family: 'Share Tech Mono', monospace !important;
    transition: all .3s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #00d4ff !important;
    box-shadow: 0 0 12px rgba(0,212,255,.3) !important;
    background: rgba(0,212,255,.07) !important;
}
.stCheckbox label, .stSelectbox label,
[data-testid="stWidgetLabel"] {
    font-family: 'Share Tech Mono', monospace !important;
    color: #93c5fd !important;
    font-size: .8rem !important;
    letter-spacing: .04em !important;
}
[data-testid="stExpander"] {
    border: 1px solid rgba(0,212,255,.18) !important;
    border-radius: 2px !important;
    background: rgba(0,212,255,.025) !important;
    box-shadow: 0 0 15px rgba(0,212,255,.04) !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Share Tech Mono', monospace !important;
    color: #67e8f9 !important;
    letter-spacing: .05em !important;
}
[data-testid="stMetric"] {
    background: rgba(0,212,255,.04);
    border: 1px solid rgba(0,212,255,.2);
    border-radius: 2px;
    padding: 12px 16px !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Orbitron', monospace !important;
    color: #00d4ff !important;
    text-shadow: 0 0 14px rgba(0,212,255,.6) !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'Share Tech Mono', monospace !important;
    color: rgba(100,200,255,.6) !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    font-size: .65rem !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(0,212,255,.18) !important;
    border-radius: 2px !important;
    box-shadow: 0 0 30px rgba(0,212,255,.06) !important;
}
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #00d4ff, #a855f7) !important;
    box-shadow: 0 0 8px rgba(0,212,255,.5) !important;
}
[data-testid="stAlert"] {
    font-family: 'Share Tech Mono', monospace !important;
    border-radius: 2px !important;
    border-left-width: 3px !important;
    font-size: .8rem !important;
}
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(0,212,255,.4), rgba(168,85,247,.4), transparent) !important;
    margin: 1.5rem 0 !important;
}
p, li {
    font-family: 'Share Tech Mono', monospace !important;
    color: #b0d4f0 !important;
    line-height: 1.7 !important;
}
.stCaption p {
    color: rgba(100,180,220,.55) !important;
    font-size: .72rem !important;
    letter-spacing: .03em !important;
}
code {
    background: rgba(0,212,255,.1) !important;
    color: #00d4ff !important;
    border: 1px solid rgba(0,212,255,.2) !important;
    border-radius: 2px !important;
    font-family: 'Share Tech Mono', monospace !important;
    padding: 1px 5px !important;
}
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #07090f; }
::-webkit-scrollbar-thumb { background: rgba(0,212,255,.25); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,212,255,.5); }
[data-testid="stToast"] {
    background: #0b0f1e !important;
    border: 1px solid rgba(0,212,255,.3) !important;
    font-family: 'Share Tech Mono', monospace !important;
    box-shadow: 0 0 20px rgba(0,212,255,.15) !important;
}
table { border-collapse: collapse !important; width: 100% !important; }
thead tr { border-bottom: 1px solid rgba(0,212,255,.3) !important; }
th {
    font-family: 'Share Tech Mono', monospace !important;
    color: #00d4ff !important;
    font-size: .75rem !important;
    letter-spacing: .08em !important;
    text-transform: uppercase !important;
    padding: 6px 12px !important;
}
td {
    font-family: 'Share Tech Mono', monospace !important;
    color: #b0d4f0 !important;
    font-size: .78rem !important;
    padding: 5px 12px !important;
    border-bottom: 1px solid rgba(0,212,255,.07) !important;
}
tr:hover td { background: rgba(0,212,255,.04) !important; }
/* Tab styling */
[data-testid="stTabs"] button {
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: .06em !important;
    font-size: .8rem !important;
}
</style>
"""

# ─── Configurazione ───────────────────────────────────────────────────────────

DEFAULT_TICKERS = [
    # Big Tech — cloud, modelli AI, ecosistema
    "MSFT", "GOOGL", "AMZN", "META", "AAPL", "TSLA",
    # Semiconduttori AI — chip, architetture, memoria, produzione
    "NVDA", "AMD", "AVGO", "ARM", "MRVL", "MU", "TSM", "SMCI", "QCOM", "INTC", "ASML",
    # Networking & datacenter AI
    "ANET", "NET",
    # AI Software & piattaforme enterprise
    "PLTR", "NOW", "CRM", "SNOW", "CDNS", "SNPS", "ORCL", "ADBE", "PATH", "AI",
    # AI applicata & dati
    "NFLX", "UBER", "SOUN", "DDOG", "ACN",
    # Finance & consumer
    "JPM", "BAC", "V", "MA", "JNJ", "PFE", "KO", "DIS", "SBUX", "RACE",
]

RATING_RANK: Dict[str, int] = {
    "strong_buy":   5,
    "buy":          4,
    "hold":         3,
    "underperform": 2,
    "sell":         1,
    "strong_sell":  0,
}

RATING_LABEL: Dict[str, str] = {
    "strong_buy":   "⭐ Strong Buy",
    "buy":          "✅ Buy",
    "hold":         "➡️ Hold",
    "underperform": "⚠️ Underperform",
    "sell":         "🔻 Sell",
    "strong_sell":  "❌ Strong Sell",
}

RATING_COLORS: Dict[str, str] = {
    "⭐ Strong Buy":   "background-color: #1b5e20; color: white",
    "✅ Buy":          "background-color: #388e3c; color: white",
    "➡️ Hold":         "background-color: #f57c00; color: black",
    "⚠️ Underperform": "background-color: #e53935; color: white",
    "🔻 Sell":         "background-color: #b71c1c; color: white",
    "❌ Strong Sell":  "background-color: #4a148c; color: white",
}

TICKER_ISIN: Dict[str, str] = {
    "AAPL":  "US0378331005", "MSFT":  "US5949181045", "NVDA":  "US67066G1040",
    "TSLA":  "US88160R1014", "AMZN":  "US0231351067", "META":  "US30303M1027",
    "GOOGL": "US02079K3059", "NFLX":  "US64110L1061", "AMD":   "US0079031078",
    "INTC":  "US4581401001", "CRM":   "US79466L3024", "ORCL":  "US68389X1054",
    "QCOM":  "US7475251036", "UBER":  "US90353T1007", "JPM":   "US46625H1005",
    "BAC":   "US0605051046", "V":     "US92826C8394", "MA":    "US57636Q1040",
    "JNJ":   "US4781601046", "PFE":   "US7170811035", "KO":    "US1912161007",
    "DIS":   "US2546871060", "SBUX":  "US8552441094", "ASML":  "NL0010273215",
    "RACE":  "NL0011585146", "AVGO":  "US11135F1012", "MU":    "US5951121038",
    "TSM":   "US8740391003", "MRVL":  "US5738741041", "ANET":  "US0404131064",
    "PLTR":  "US69608A1088", "ADBE":  "US00724F1012", "NOW":   "US81762P1021",
    "CDNS":  "US1273871051", "SNPS":  "US8716071076", "PATH":  "US90364P1057",
    "SNOW":  "US8334451098", "DDOG":  "US23804L1035", "NET":   "US18915M1071",
    "ACN":   "IE00B4BNMY34",
    # Europei (aggiungibili come ticker personalizzati)
    "MC.PA": "FR0000121014", "VOW3.DE": "DE0007664039", "SAP.DE": "DE0007164600",
    "ENI.MI": "IT0003132476", "STLAM.MI": "NL00150001Q9",
    "UCG.MI": "IT0005239360", "ISP.MI": "IT0000072618",
}

ISIN_TICKER: Dict[str, str] = {isin: ticker for ticker, isin in TICKER_ISIN.items()}
_ISIN_RE = re.compile(r'^[A-Z]{2}[A-Z0-9]{10}$')

EXCHANGE_MAP = {
    ".MI": ":IM", ".PA": ":FP", ".DE": ":GR",
    ".AS": ":NA", ".L":  ":LN", ".SW": ":SW", ".BR": ":BB",
}
BULLISH = {"strong_buy", "buy"}
BEARISH = {"sell", "strong_sell"}

CURRENCY_SYMBOL: Dict[str, str] = {
    "USD": "$", "EUR": "€", "GBP": "£", "CHF": "Fr",
    "JPY": "¥", "GBp": "p", "CAD": "C$", "AUD": "A$",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def resolve_input(raw: str) -> tuple[str | None, str | None]:
    s = raw.strip().upper()
    if _ISIN_RE.match(s):
        ticker = ISIN_TICKER.get(s)
        if ticker:
            return ticker, None
        return None, f"ISIN `{s}` non presente nella mappa — aggiungi il ticker direttamente."
    return s, None


def yahoo_to_finnhub(ticker: str) -> str:
    for yahoo_sfx, fh_sfx in EXCHANGE_MAP.items():
        if ticker.endswith(yahoo_sfx):
            return ticker[: -len(yahoo_sfx)] + fh_sfx
    return ticker


def compute_fh_label(sb, b, h, s, ss) -> str | None:
    total = (sb or 0) + (b or 0) + (h or 0) + (s or 0) + (ss or 0)
    if total == 0:
        return None
    score = (5*(sb or 0) + 4*(b or 0) + 3*(h or 0) + 2*(s or 0) + 1*(ss or 0)) / total
    if score >= 4.5: return "strong_buy"
    if score >= 3.5: return "buy"
    if score >= 2.5: return "hold"
    if score >= 1.5: return "sell"
    return "strong_sell"


def _period_score(p: dict) -> float:
    sb = int(p.get("strongBuy",  0) or 0)
    b  = int(p.get("buy",        0) or 0)
    h  = int(p.get("hold",       0) or 0)
    s  = int(p.get("sell",       0) or 0)
    ss = int(p.get("strongSell", 0) or 0)
    t  = sb + b + h + s + ss
    return (5*sb + 4*b + 3*h + 2*s + 1*ss) / t if t else 0.0


def compute_accordo(yahoo_rating: str, fh_label: str | None) -> str:
    if fh_label is None:
        return "❓ Solo Yahoo"
    y = yahoo_rating.lower()
    if y in BULLISH and fh_label in BULLISH:   return "✅ Concordano"
    if y == "hold" and fh_label == "hold":      return "✅ Concordano"
    if y in BEARISH and fh_label in BEARISH:    return "✅ Concordano"
    return "⚠️ Discordano"


def compute_score(yahoo_rating: str, fh_sb_pct, upside, fh_trend: str, accordo: str) -> int:
    """Score composito 0–100: Yahoo(35) + FH SB%(30) + Upside%(20) + Trend(10) + Accordo(5)."""
    pts: float = 0

    yahoo_pts = {"strong_buy": 35, "buy": 25, "hold": 12,
                 "underperform": 5, "sell": 2, "strong_sell": 0}
    pts += yahoo_pts.get(str(yahoo_rating).lower(), 0)

    if fh_sb_pct is not None and pd.notna(fh_sb_pct):
        pts += min(float(fh_sb_pct) * 0.30, 30)

    if upside is not None and pd.notna(upside):
        clipped = max(-40.0, min(80.0, float(upside)))
        pts += (clipped + 40) / 120 * 20

    trend_pts = {"↑ In crescita": 10, "→ Stabile": 5, "↓ In calo": 0}
    pts += trend_pts.get(fh_trend, 3)

    accordo_pts = {"✅ Concordano": 5, "⚠️ Discordano": 0, "❓ Solo Yahoo": 2}
    pts += accordo_pts.get(accordo, 0)

    return min(100, max(0, round(pts)))


# ─── Recupero dati ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(ticker: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "current_price": None, "yahoo_rating": None,
        "target_high": None, "target_low": None, "target_mean": None,
        "name": None, "currency": None, "error": None,
        "pe_trailing": None, "pe_forward": None, "beta": None,
        "market_cap": None, "revenue_growth": None, "earnings_growth": None,
        "dividend_yield": None, "debt_to_equity": None,
        "week52_high": None, "week52_low": None,
    }
    try:
        info = yf.Ticker(ticker).info
        if not info.get("symbol") and not info.get("currentPrice") and not info.get("regularMarketPrice"):
            result["error"] = "Ticker non trovato su Yahoo Finance"
            return result
        result.update({
            "yahoo_rating":    info.get("recommendationKey"),
            "current_price":   info.get("currentPrice") or info.get("regularMarketPrice"),
            "target_high":     info.get("targetHighPrice"),
            "target_low":      info.get("targetLowPrice"),
            "target_mean":     info.get("targetMeanPrice"),
            "name":            info.get("shortName") or info.get("longName"),
            "currency":        info.get("currency"),
            "pe_trailing":     info.get("trailingPE"),
            "pe_forward":      info.get("forwardPE"),
            "beta":            info.get("beta"),
            "market_cap":      info.get("marketCap"),
            "revenue_growth":  info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "dividend_yield":  info.get("dividendYield"),
            "debt_to_equity":  info.get("debtToEquity"),
            "week52_high":     info.get("fiftyTwoWeekHigh"),
            "week52_low":      info.get("fiftyTwoWeekLow"),
        })
    except Exception as exc:
        result["error"] = str(exc)
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def get_finnhub_data(ticker: str, api_key: str) -> Dict[str, Any]:
    fh_ticker = yahoo_to_finnhub(ticker)
    result: Dict[str, Any] = {
        "fh_strong_buy": None, "fh_buy": None, "fh_hold": None,
        "fh_sell": None, "fh_strong_sell": None, "fh_total": None,
        "fh_ticker_used": fh_ticker, "fh_trend": None, "error": None,
    }
    if not api_key:
        return result
    try:
        resp = requests.get(
            "https://finnhub.io/api/v1/stock/recommendation",
            params={"symbol": fh_ticker, "token": api_key},
            timeout=10,
        )
        if resp.status_code == 401:
            result["error"] = "API Key non valida"; return result
        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}"; return result
        data = resp.json()
        if not data:
            result["error"] = f"Nessun dato (cercato come '{fh_ticker}')"; return result

        latest = data[0]
        sb  = int(latest.get("strongBuy",  0) or 0)
        b   = int(latest.get("buy",        0) or 0)
        h   = int(latest.get("hold",       0) or 0)
        s   = int(latest.get("sell",       0) or 0)
        ss  = int(latest.get("strongSell", 0) or 0)
        total = sb + b + h + s + ss

        # Trend: confronta periodo corrente con ~6 mesi fa
        if len(data) >= 3:
            diff = _period_score(data[0]) - _period_score(data[2])
            trend = "↑ In crescita" if diff > 0.15 else ("↓ In calo" if diff < -0.15 else "→ Stabile")
        else:
            trend = "→ Stabile"

        result.update({
            "fh_strong_buy":  sb,   "fh_buy":   b,
            "fh_hold":        h,    "fh_sell":  s,
            "fh_strong_sell": ss,
            "fh_total":       total if total > 0 else None,
            "fh_trend":       trend,
        })
    except Exception as exc:
        result["error"] = str(exc)
    return result


@st.cache_data(ttl=1800, show_spinner=False)
def get_fear_greed() -> Dict[str, Any] | None:
    try:
        resp = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        if resp.status_code == 200:
            fg = resp.json().get("fear_and_greed", {})
            score = fg.get("score")
            rating = fg.get("rating", "").replace("_", " ").title()
            if score is not None:
                return {"score": round(float(score)), "rating": rating}
    except Exception:
        pass
    return None


# ─── Costruzione DataFrame ────────────────────────────────────────────────────

def build_dataframe(
    tickers: list,
    finnhub_key: str,
    progress_bar,
) -> tuple[pd.DataFrame, list[str]]:
    rows, warnings = [], []
    n = len(tickers)

    for i, ticker in enumerate(tickers):
        progress_bar.progress((i + 1) / n, text=f"Analisi {ticker}  ({i + 1}/{n})...")
        y  = get_yahoo_data(ticker)
        fh = get_finnhub_data(ticker, finnhub_key)

        if y["error"]:
            warnings.append(f"**{ticker}** — Yahoo Finance: {y['error']}")
        if fh["error"] and finnhub_key:
            fh_t  = fh["fh_ticker_used"]
            label = f" (cercato come `{fh_t}`)" if fh_t != ticker else ""
            warnings.append(f"**{ticker}**{label} — Finnhub: {fh['error']}")

        fh_total = fh["fh_total"]
        fh_sb    = fh["fh_strong_buy"]
        fh_pct: float | None = (
            round(fh_sb / fh_total * 100, 1)
            if fh_sb is not None and fh_total and fh_total > 0 else None
        )

        price    = y["current_price"]
        tgt_mean = y["target_mean"]
        upside: float | None = (
            round((tgt_mean - price) / price * 100, 1)
            if price and tgt_mean and price > 0 else None
        )

        yahoo_rating = y["yahoo_rating"] or "N/D"
        fh_label     = compute_fh_label(fh_sb, fh["fh_buy"], fh["fh_hold"], fh["fh_sell"], fh["fh_strong_sell"])
        accordo      = compute_accordo(yahoo_rating, fh_label)
        fh_trend     = fh["fh_trend"] or "N/D"
        score        = compute_score(yahoo_rating, fh_pct, upside, fh_trend, accordo)

        rows.append({
            "Ticker":          ticker,
            "Nome":            y["name"] or "N/D",
            "ISIN":            TICKER_ISIN.get(ticker, "N/D"),
            "Score":           score,
            "Prezzo":          price,
            "Valuta":          y["currency"] or "N/D",
            "Yahoo Rating":    yahoo_rating,
            "Finnhub Rating":  fh_label,
            "Accordo":         accordo,
            "FH Trend":        fh_trend,
            "Upside %":        upside,
            "Target Low":      y["target_low"],
            "Target Mean":     tgt_mean,
            "Target High":     y["target_high"],
            "FH SB %":         fh_pct,
            "Analisti FH":     fh_total,
            "FH Strong Buy":   fh_sb,
            "FH Buy":          fh["fh_buy"],
            "FH Hold":         fh["fh_hold"],
            "FH Sell":         fh["fh_sell"],
            "FH Strong Sell":  fh["fh_strong_sell"],
            # Fondamentali
            "P/E Trailing":    y["pe_trailing"],
            "P/E Forward":     y["pe_forward"],
            "Beta":            y["beta"],
            "Market Cap":      y["market_cap"],
            "Rev. Growth":     y["revenue_growth"],
            "EPS Growth":      y["earnings_growth"],
            "Div. Yield":      y["dividend_yield"],
            "Debt/Equity":     y["debt_to_equity"],
            "52w High":        y["week52_high"],
            "52w Low":         y["week52_low"],
        })

    df = pd.DataFrame(rows)
    df["_rank"]    = df["Yahoo Rating"].map(lambda x: RATING_RANK.get(x, -1))
    df["_fh_sort"] = df["FH SB %"].fillna(0.0)
    df = (
        df.sort_values(["_rank", "_fh_sort"], ascending=[False, False])
          .drop(columns=["_rank", "_fh_sort"])
          .reset_index(drop=True)
    )
    return df, warnings


# ─── Logica Consenso Assoluto ─────────────────────────────────────────────────

def is_consenso_assoluto(row: pd.Series) -> bool:
    yahoo_ok = row["Yahoo Rating"] == "strong_buy"
    fh_pct   = row.get("FH SB %")
    fh_ok    = fh_pct is not None and pd.notna(fh_pct) and float(fh_pct) > 50.0
    return bool(yahoo_ok and fh_ok)


# ─── Formattazione ────────────────────────────────────────────────────────────

def _fmt_price(val, currency: str = "") -> str:
    try:
        if pd.isna(val): return "N/D"
        symbol = CURRENCY_SYMBOL.get(currency, currency)
        return f"{symbol} {float(val):,.2f}".strip()
    except (TypeError, ValueError):
        return "N/D"

def _fmt_int(val) -> str:
    try: return str(int(val)) if pd.notna(val) else "N/D"
    except (TypeError, ValueError): return "N/D"

def _fmt_pct(val) -> str:
    try: return f"{float(val):.1f}%" if pd.notna(val) else "N/D"
    except (TypeError, ValueError): return "N/D"

def _fmt_upside(val) -> str:
    try:
        if pd.isna(val): return "N/D"
        v = float(val)
        return f"{'+'if v>0 else ''}{v:.1f}%"
    except (TypeError, ValueError): return "N/D"

def _fmt_pe(val) -> str:
    try: return f"{float(val):.1f}x" if pd.notna(val) else "N/D"
    except (TypeError, ValueError): return "N/D"

def _fmt_ratio(val) -> str:
    try: return f"{float(val):.2f}" if pd.notna(val) else "N/D"
    except (TypeError, ValueError): return "N/D"

def _fmt_growth(val) -> str:
    try:
        if pd.isna(val): return "N/D"
        v = float(val) * 100
        return f"{'+'if v>0 else ''}{v:.1f}%"
    except (TypeError, ValueError): return "N/D"

def _fmt_market_cap(val) -> str:
    try:
        if pd.isna(val): return "N/D"
        v = float(val)
        if v >= 1e12: return f"$ {v/1e12:.2f}T"
        if v >= 1e9:  return f"$ {v/1e9:.1f}B"
        return f"$ {v/1e6:.0f}M"
    except (TypeError, ValueError): return "N/D"


DISPLAY_COLS = [
    "Ticker", "Nome", "Score", "Prezzo", "Yahoo Rating", "Finnhub Rating",
    "Accordo", "FH Trend", "Upside %", "FH SB %", "Analisti FH",
]

FUNDAMENTALS_COLS = [
    "Ticker", "Nome", "Market Cap", "P/E Trailing", "P/E Forward",
    "Beta", "Rev. Growth", "EPS Growth", "Div. Yield", "Debt/Equity",
    "52w Low", "52w High",
]


def format_for_display(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["Yahoo Rating"]   = d["Yahoo Rating"].map(lambda x: RATING_LABEL.get(str(x).lower(), x))
    d["Finnhub Rating"] = d["Finnhub Rating"].map(
        lambda x: RATING_LABEL.get(str(x).lower(), "N/D") if x else "N/D"
    )
    d["Prezzo"]      = d.apply(lambda r: _fmt_price(r["Prezzo"], r.get("Valuta", "")), axis=1)
    d["FH SB %"]     = d["FH SB %"].apply(_fmt_pct)
    d["Upside %"]    = d["Upside %"].apply(_fmt_upside)
    d["Analisti FH"] = d["Analisti FH"].apply(_fmt_int)
    return d[DISPLAY_COLS]


def format_fundamentals(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["Market Cap"]   = d["Market Cap"].apply(_fmt_market_cap)
    d["P/E Trailing"] = d["P/E Trailing"].apply(_fmt_pe)
    d["P/E Forward"]  = d["P/E Forward"].apply(_fmt_pe)
    d["Beta"]         = d["Beta"].apply(_fmt_ratio)
    d["Rev. Growth"]  = d["Rev. Growth"].apply(_fmt_growth)
    d["EPS Growth"]   = d["EPS Growth"].apply(_fmt_growth)
    d["Div. Yield"]   = d["Div. Yield"].apply(_fmt_growth)
    d["Debt/Equity"]  = d["Debt/Equity"].apply(_fmt_ratio)
    d["52w Low"]      = d.apply(lambda r: _fmt_price(r["52w Low"],  r.get("Valuta", "")), axis=1)
    d["52w High"]     = d.apply(lambda r: _fmt_price(r["52w High"], r.get("Valuta", "")), axis=1)
    return d[FUNDAMENTALS_COLS]


# ─── Colori ───────────────────────────────────────────────────────────────────

def color_rating(val: str) -> str:
    return RATING_COLORS.get(str(val), "")

def color_upside(val: str) -> str:
    if not val or val == "N/D": return ""
    try:
        v = float(str(val).replace("%", "").replace("+", ""))
        if v > 0:  return "color: #4caf50; font-weight: bold"
        if v < 0:  return "color: #f44336; font-weight: bold"
    except ValueError: pass
    return ""

def color_accordo(val: str) -> str:
    if val.startswith("✅"): return "color: #4caf50; font-weight: bold"
    if val.startswith("⚠️"): return "color: #ff9800; font-weight: bold"
    return "color: #78909c"

def color_trend(val: str) -> str:
    if "crescita" in str(val): return "color: #4caf50; font-weight: bold"
    if "calo"     in str(val): return "color: #f44336; font-weight: bold"
    return "color: #78909c"

def color_score(val) -> str:
    try:
        v = int(val)
        if v >= 75: return "background-color: #1b5e20; color: white; font-weight: bold"
        if v >= 55: return "background-color: #2e7d32; color: white"
        if v >= 40: return "background-color: #e65100; color: white"
        if v >= 25: return "background-color: #b71c1c; color: white"
        return "background-color: #4a148c; color: white"
    except (TypeError, ValueError): return ""

def color_growth(val: str) -> str:
    if not val or val == "N/D": return ""
    try:
        v = float(str(val).replace("%", "").replace("+", ""))
        if v > 0:  return "color: #4caf50"
        if v < 0:  return "color: #f44336"
    except ValueError: pass
    return ""

def style_table(display_df: pd.DataFrame):
    cols = display_df.columns.tolist()
    s = display_df.style
    for col, fn in [
        ("Yahoo Rating", color_rating), ("Finnhub Rating", color_rating),
        ("Upside %", color_upside), ("Accordo", color_accordo),
        ("FH Trend", color_trend), ("Score", color_score),
    ]:
        if col in cols:
            s = s.map(fn, subset=[col])
    return s

def style_fundamentals(display_df: pd.DataFrame):
    cols = display_df.columns.tolist()
    s = display_df.style
    for col in ["Rev. Growth", "EPS Growth", "Div. Yield"]:
        if col in cols:
            s = s.map(color_growth, subset=[col])
    return s


# ─── Grafici ─────────────────────────────────────────────────────────────────

PLOTLY_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#c8e8ff", family="Share Tech Mono"),
    xaxis=dict(gridcolor="rgba(0,212,255,0.12)", zerolinecolor="rgba(0,212,255,0.2)"),
    yaxis=dict(gridcolor="rgba(0,212,255,0.12)", zerolinecolor="rgba(0,212,255,0.2)"),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,212,255,0.2)"),
)

FH_COLOR_MAP = {
    "⭐ Strong Buy": "#1b5e20", "✅ Buy": "#4caf50",
    "➡️ Hold": "#ff9800", "⚠️ Underperform": "#f44336",
    "🔻 Sell": "#b71c1c", "❌ Strong Sell": "#7b1fa2",
    "N/D": "#546e7a",
}


def make_scatter_chart(df: pd.DataFrame):
    plot_df = df.dropna(subset=["FH SB %", "Upside %"]).copy()
    if plot_df.empty:
        return None
    plot_df["Yahoo Label"]    = plot_df["Yahoo Rating"].map(lambda x: RATING_LABEL.get(str(x).lower(), x))
    plot_df["Analisti FH"]    = plot_df["Analisti FH"].fillna(10)
    plot_df["Score display"]  = plot_df["Score"].astype(str)

    fig = px.scatter(
        plot_df, x="FH SB %", y="Upside %",
        size="Analisti FH", color="Yahoo Label",
        color_discrete_map=FH_COLOR_MAP,
        text="Ticker", hover_name="Nome",
        hover_data={"Score display": True, "Accordo": True,
                    "Yahoo Label": False, "Analisti FH": True},
        size_max=45,
        labels={"FH SB %": "Finnhub Strong Buy %", "Upside %": "Upside %"},
    )
    fig.update_traces(textposition="top center", textfont=dict(size=9, color="#e0f0ff"))
    fig.add_hline(y=0,  line_dash="dash", line_color="rgba(200,200,200,0.25)", annotation_text="Upside 0%")
    fig.add_vline(x=30, line_dash="dash", line_color="rgba(200,200,200,0.25)", annotation_text="FH SB 30%")
    fig.update_layout(**PLOTLY_LAYOUT, height=520,
                      title=dict(text="Scatter: Upside % vs Finnhub Strong Buy %", font=dict(size=13)))
    return fig


def make_target_chart(df: pd.DataFrame, top_n: int = 15):
    plot_df = df.dropna(subset=["Prezzo", "Target Low", "Target Mean", "Target High"]).head(top_n).copy()
    if plot_df.empty:
        return None

    fig = go.Figure()
    tickers = plot_df["Ticker"].tolist()

    for _, row in plot_df.iterrows():
        t     = row["Ticker"]
        price = float(row["Prezzo"])
        tlow  = float(row["Target Low"])
        tmean = float(row["Target Mean"])
        thigh = float(row["Target High"])

        fig.add_trace(go.Bar(
            name=t, x=[t],
            y=[thigh - tlow], base=[tlow],
            marker_color="rgba(0,212,255,0.12)",
            marker_line=dict(color="rgba(0,212,255,0.35)", width=1),
            showlegend=False, width=0.5,
        ))
        fig.add_trace(go.Scatter(
            x=[t], y=[tmean], mode="markers",
            marker=dict(symbol="line-ew-open", size=22, color="#a855f7",
                        line=dict(width=3, color="#a855f7")),
            showlegend=False, hovertemplate=f"<b>{t}</b><br>Target Mean: {tmean:.2f}<extra></extra>",
        ))
        color = "#00d4ff" if price <= tmean else "#f44336"
        fig.add_trace(go.Scatter(
            x=[t], y=[price], mode="markers",
            marker=dict(symbol="diamond", size=10, color=color,
                        line=dict(width=1, color="white")),
            showlegend=False, hovertemplate=f"<b>{t}</b><br>Prezzo: {price:.2f}<extra></extra>",
        ))

    base = {k: v for k, v in PLOTLY_LAYOUT.items() if k != "xaxis"}
    fig.update_layout(
        **base, height=480, barmode="overlay",
        xaxis=dict(categoryorder="array", categoryarray=tickers,
                   gridcolor="rgba(0,212,255,0.12)", zerolinecolor="rgba(0,212,255,0.2)"),
        title=dict(text=f"Prezzo attuale vs Target Low / Mean / High (top {top_n} per Score)",
                   font=dict(size=13)),
    )
    fig.add_annotation(x=0.01, y=1.06, xref="paper", yref="paper",
                       text="◆ Prezzo attuale  ─── Target Mean  ▌Range Target",
                       showarrow=False, font=dict(size=10, color="#90a4ae"), xanchor="left")
    return fig


# ─── App principale ───────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(page_title="Analisti BuySell", page_icon="📈", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.markdown("""
<div style="text-align:center; padding:1.2rem 0 0.4rem 0;">
    <div style="font-family:'Share Tech Mono',monospace; font-size:.65rem; letter-spacing:.55em;
                color:rgba(0,212,255,.45); text-transform:uppercase; margin-bottom:.6rem;">
        ◈ &nbsp; sistema di analisi mercati azionari &nbsp; ◈
    </div>
    <h1 style="margin:0; padding:0;">📈 &nbsp; ANALISTI BUYSELL</h1>
    <div style="font-family:'Share Tech Mono',monospace; font-size:.72rem; margin-top:.6rem;
                color:rgba(0,212,255,.4); letter-spacing:.28em; text-transform:uppercase;">
        consensus scanner &nbsp;·&nbsp; yahoo finance &nbsp;×&nbsp; finnhub
    </div>
</div>
""", unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Configurazione")

        show_key = st.checkbox("Mostra API Key (per incollare)")
        if "finnhub_key" not in st.session_state:
            try:
                st.session_state["finnhub_key"] = st.secrets["finnhub"]["api_key"]
            except (KeyError, FileNotFoundError):
                st.session_state["finnhub_key"] = ""

        finnhub_key: str = st.text_input(
            "🔑 Finnhub API Key",
            value=st.session_state["finnhub_key"],
            type="default" if show_key else "password",
            placeholder="Incolla qui la tua API Key...",
        )
        st.session_state["finnhub_key"] = finnhub_key
        if finnhub_key:
            st.success("API Key inserita ✓")
        else:
            st.warning("Senza API Key vengono caricati solo i dati Yahoo Finance.")

        st.divider()
        use_default: bool = st.checkbox("Usa lista predefinita", value=True)
        st.subheader("➕ Ticker personalizzati")
        custom_raw: str = st.text_area(
            "Ticker o ISIN — uno per riga o virgola",
            placeholder="UBER\nIT0003132476 (= ENI.MI)",
            height=90,
        )

        st.subheader("💼 Il mio portafoglio")
        portfolio_raw: str = st.text_area(
            "Ticker che possiedi (uno per riga)",
            placeholder="NVDA\nMSFT\nAAPL",
            height=80,
            key="portfolio_input",
        )

        st.divider()
        run = st.button("🔍 Analizza ora", type="primary", use_container_width=True)
        if st.button("🗑️ Svuota cache dati", use_container_width=True):
            st.cache_data.clear()
            st.toast("Cache svuotata.", icon="✅")

    # ── Fear & Greed ──────────────────────────────────────────────────────────
    fg = get_fear_greed()
    if fg:
        score_fg = fg["score"]
        emoji = "😱" if score_fg < 25 else "😟" if score_fg < 45 else "😐" if score_fg < 55 else "😊" if score_fg < 75 else "🤑"
        color  = "#f44336" if score_fg < 45 else "#ff9800" if score_fg < 55 else "#4caf50"
        st.markdown(
            f'<div style="text-align:center; padding:.5rem 0; font-family:Share Tech Mono,monospace;">'
            f'<span style="font-size:.65rem; letter-spacing:.3em; color:rgba(0,212,255,.4);">SENTIMENT MERCATO (CNN F&G)</span><br>'
            f'<span style="font-size:1.6rem; font-family:Orbitron,monospace; color:{color}; '
            f'text-shadow:0 0 12px {color}88;">{score_fg}</span>'
            f'<span style="font-size:.85rem; color:{color}; margin-left:.5rem;">{emoji} {fg["rating"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.divider()

    # ── Lista ticker ──────────────────────────────────────────────────────────
    tickers: list = list(DEFAULT_TICKERS) if use_default else []
    isin_warnings = []
    if custom_raw.strip():
        for raw in custom_raw.replace(",", "\n").splitlines():
            if not raw.strip(): continue
            t, warn = resolve_input(raw)
            if warn:   isin_warnings.append(warn)
            elif t and t not in tickers: tickers.append(t)
    for w in isin_warnings:
        st.warning(w)

    if not tickers:
        st.info("Abilita la lista predefinita oppure aggiungi ticker personalizzati.")
        return

    st.markdown(
        f"**{len(tickers)} ticker:** " + "  ".join(f"`{t}`" for t in tickers)
    )

    # ── Portafoglio: parsing ──────────────────────────────────────────────────
    portfolio_tickers: list[str] = []
    if portfolio_raw.strip():
        for raw in portfolio_raw.replace(",", "\n").splitlines():
            if not raw.strip(): continue
            t, _ = resolve_input(raw)
            if t and t not in portfolio_tickers:
                portfolio_tickers.append(t)
                if t not in tickers:
                    tickers.append(t)

    # ── Analisi ───────────────────────────────────────────────────────────────
    if run:
        bar = st.progress(0, text="Avvio analisi...")
        df, warns = build_dataframe(tickers, finnhub_key, bar)
        bar.empty()
        st.session_state["df"]       = df
        st.session_state["warnings"] = warns
        st.success(f"✅ Analisi completata: {len(df)} titoli elaborati.")

    if "df" not in st.session_state:
        return

    df: pd.DataFrame  = st.session_state["df"]
    warnings: list    = st.session_state.get("warnings", [])

    # ── Expander avvisi & legenda ─────────────────────────────────────────────
    with st.expander("📖 Come leggere la tabella", expanded=False):
        st.markdown("""
| Colonna | Significato |
|---|---|
| **Score** | Punteggio composito 0–100 che combina Yahoo Rating, FH SB%, Upside%, Trend e Accordo. Verde ≥ 75, arancio 40–55, rosso < 25. |
| **Yahoo / Finnhub Rating** | Consenso degli analisti (Strong Buy → Strong Sell) dalle due fonti indipendenti. |
| **Accordo** | ✅ Le due fonti concordano · ⚠️ Discordano · ❓ Dati FH mancanti. |
| **FH Trend** | ↑ Il consenso Finnhub è migliorato negli ultimi 6 mesi · ↓ Peggiorato · → Stabile. |
| **Upside %** | Distanza % dal prezzo attuale al Target Mean degli analisti. Verde = potenziale salita. |
| **FH SB %** | % di analisti Finnhub con rating massimo "Strong Buy". |
| **Analisti FH** | Numero di analisti che coprono il titolo su Finnhub. |
| **P/E Trailing / Forward** | Prezzo / Utile. Misura quanto il mercato paga gli utili. Basso = più economico. |
| **Beta** | Volatilità vs mercato. > 1 = più volatile, < 1 = meno volatile. |
| **Rev. / EPS Growth** | Crescita ricavi e utili YoY. Verde = crescita, rosso = contrazione. |
        """)

    if warnings:
        with st.expander(f"⚠️ {len(warnings)} avvisi tecnici", expanded=False):
            for w in warnings: st.markdown(f"- {w}")

    # ── TABS ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⭐ Top Picks", "📊 Tabella", "📈 Fondamentali", "🔭 Grafici", "💼 Portafoglio"
    ])

    # ── Tab 1: Top Picks ─────────────────────────────────────────────────────
    with tab1:
        mask_ca   = df.apply(is_consenso_assoluto, axis=1)
        df_ca     = df[mask_ca].reset_index(drop=True)
        df_top    = df[df["Score"] >= 70].reset_index(drop=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Consenso Assoluto", len(df_ca))
        c2.metric("Score ≥ 70", len(df_top))
        c3.metric("Analizzati", len(df))

        st.subheader("⭐ Consenso Assoluto")
        st.caption("Yahoo = **Strong Buy** e Finnhub Strong Buy > 50% — doppio filtro anti-rumore.")
        if df_ca.empty:
            st.info("Nessun titolo soddisfa entrambi i criteri al momento.")
        else:
            st.dataframe(style_table(format_for_display(df_ca)), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🔥 Titoli con Score ≥ 70")
        st.caption("Punteggio composito alto = segnale forte su più dimensioni.")
        if df_top.empty:
            st.info("Nessun titolo con Score ≥ 70 al momento.")
        else:
            st.dataframe(style_table(format_for_display(df_top)), use_container_width=True, hide_index=True)

    # ── Tab 2: Tabella completa ───────────────────────────────────────────────
    with tab2:
        st.subheader("📊 Tutti i titoli analizzati")
        st.caption("Ordinati per Yahoo Rating · FH SB%. Clicca un'intestazione per riordinare.")
        st.dataframe(style_table(format_for_display(df)), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Scarica CSV completo",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="analisti_buysell.csv", mime="text/csv",
        )

    # ── Tab 3: Fondamentali ───────────────────────────────────────────────────
    with tab3:
        st.subheader("📈 Dati Fondamentali")
        st.caption(
            "**P/E**: prezzo / utile — più basso = più economico rispetto agli utili.  "
            "**Beta**: volatilità (>1 = più volatile del mercato).  "
            "**Rev./EPS Growth**: crescita ricavi e utili YoY.  "
            "**Div. Yield**: rendimento dividendo annuo.  "
            "**Debt/Equity**: leva finanziaria."
        )
        st.dataframe(
            style_fundamentals(format_fundamentals(df)),
            use_container_width=True, hide_index=True,
        )

    # ── Tab 4: Grafici ────────────────────────────────────────────────────────
    with tab4:
        st.subheader("🔭 Grafici di Analisi")

        fig_scatter = make_scatter_chart(df)
        if fig_scatter:
            st.plotly_chart(fig_scatter, use_container_width=True)
            st.caption(
                "Quadrante in alto a destra = Upside alto + molti analisti Strong Buy — il più interessante. "
                "La dimensione del cerchio = numero di analisti (copertura più ampia = più affidabile)."
            )
        else:
            st.info("Dati insufficienti per il grafico scatter.")

        st.divider()

        fig_target = make_target_chart(df)
        if fig_target:
            st.plotly_chart(fig_target, use_container_width=True)
            st.caption(
                "Barre = range Target Low → High. "
                "Linea viola = Target Mean. "
                "Diamante **cyan** = prezzo sotto target (potenziale salita) · "
                "Diamante **rosso** = prezzo sopra target."
            )
        else:
            st.info("Dati insufficienti per il grafico prezzi/target.")

    # ── Tab 5: Portafoglio ────────────────────────────────────────────────────
    with tab5:
        st.subheader("💼 Il Mio Portafoglio")

        if not portfolio_tickers:
            st.info("Aggiungi i ticker che possiedi nella sidebar sotto **'Il mio portafoglio'**.")
        else:
            df_pf = df[df["Ticker"].isin(portfolio_tickers)].reset_index(drop=True)
            if df_pf.empty:
                st.warning("Nessun titolo del portafoglio trovato nei dati. Premi 'Analizza ora'.")
            else:
                avg_score  = round(df_pf["Score"].mean())
                n_strong   = (df_pf["Yahoo Rating"] == "strong_buy").sum()
                n_buy      = (df_pf["Yahoo Rating"] == "buy").sum()
                n_hold     = (df_pf["Yahoo Rating"] == "hold").sum()
                avg_upside = df_pf["Upside %"].dropna().mean()

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Titoli monitorati", len(df_pf))
                c2.metric("Score medio", avg_score)
                c3.metric("Strong Buy", n_strong)
                c4.metric("Buy", n_buy)
                c5.metric("Hold / altro", len(df_pf) - n_strong - n_buy)

                if pd.notna(avg_upside):
                    sign = "+" if avg_upside > 0 else ""
                    st.metric("Upside % medio portafoglio", f"{sign}{avg_upside:.1f}%")

                st.divider()
                st.dataframe(
                    style_table(format_for_display(df_pf)),
                    use_container_width=True, hide_index=True,
                )


if __name__ == "__main__":
    main()
