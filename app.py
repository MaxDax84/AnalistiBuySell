"""
Analisti BuySell — Streamlit app
Confronta il consenso degli analisti da Yahoo Finance e Finnhub.
"""

import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from typing import Dict, Any

# ─── Configurazione ───────────────────────────────────────────────────────────

DEFAULT_TICKERS = [
    # US Tech
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "NFLX",
    "AMD", "INTC", "CRM", "ORCL", "QCOM", "UBER",
    # US Finance & Consumer
    "JPM", "BAC", "V", "MA", "JNJ", "PFE", "KO", "DIS", "SBUX",
    # US-listed (copertura Finnhub disponibile)
    "ASML", "RACE",
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

# ISIN per i ticker predefiniti — per ticker personalizzati mostra N/D
TICKER_ISIN: Dict[str, str] = {
    "AAPL":  "US0378331005",
    "MSFT":  "US5949181045",
    "NVDA":  "US67066G1040",
    "TSLA":  "US88160R1014",
    "AMZN":  "US0231351067",
    "META":  "US30303M1027",
    "GOOGL": "US02079K3059",
    "NFLX":  "US64110L1061",
    "AMD":   "US0079031078",
    "INTC":  "US4581401001",
    "CRM":   "US79466L3024",
    "ORCL":  "US68389X1054",
    "QCOM":  "US7475251036",
    "UBER":  "US90353T1007",
    "JPM":   "US46625H1005",
    "BAC":   "US0605051046",
    "V":     "US92826C8394",
    "MA":    "US57636Q1040",
    "JNJ":   "US4781601046",
    "PFE":   "US7170811035",
    "KO":    "US1912161007",
    "DIS":   "US2546871060",
    "SBUX":  "US8552441094",
    "ASML":  "NL0010273215",
    "RACE":  "NL0011585146",
    # Europei (Finnhub non li copre, ma ISIN disponibile se aggiunti manualmente)
    "MC.PA":    "FR0000121014",  # LVMH
    "VOW3.DE":  "DE0007664039",  # Volkswagen
    "SAP.DE":   "DE0007164600",  # SAP
    "ENI.MI":   "IT0003132476",  # Eni
    "STLAM.MI": "NL00150001Q9",  # Stellantis
    "UCG.MI":   "IT0005239360",  # UniCredit
    "ISP.MI":   "IT0000072618",  # Intesa Sanpaolo
}

# Mappa suffissi Yahoo Finance → Finnhub per borse europee
EXCHANGE_MAP = {
    ".MI": ":IM",
    ".PA": ":FP",
    ".DE": ":GR",
    ".AS": ":NA",
    ".L":  ":LN",
    ".SW": ":SW",
    ".BR": ":BB",
}

BULLISH = {"strong_buy", "buy"}
BEARISH = {"sell", "strong_sell"}


def yahoo_to_finnhub(ticker: str) -> str:
    for yahoo_sfx, fh_sfx in EXCHANGE_MAP.items():
        if ticker.endswith(yahoo_sfx):
            return ticker[: -len(yahoo_sfx)] + fh_sfx
    return ticker


def compute_fh_label(sb, b, h, s, ss) -> str | None:
    """Rating sintetico Finnhub calcolato come media ponderata (5=SB, 4=B, 3=H, 2=S, 1=SS)."""
    total = (sb or 0) + (b or 0) + (h or 0) + (s or 0) + (ss or 0)
    if total == 0:
        return None
    score = (5*(sb or 0) + 4*(b or 0) + 3*(h or 0) + 2*(s or 0) + 1*(ss or 0)) / total
    if score >= 4.5:
        return "strong_buy"
    if score >= 3.5:
        return "buy"
    if score >= 2.5:
        return "hold"
    if score >= 1.5:
        return "sell"
    return "strong_sell"


def compute_accordo(yahoo_rating: str, fh_label: str | None) -> str:
    if fh_label is None:
        return "❓ Solo Yahoo"
    y = yahoo_rating.lower()
    if y in BULLISH and fh_label in BULLISH:
        return "✅ Concordano"
    if y == "hold" and fh_label == "hold":
        return "✅ Concordano"
    if y in BEARISH and fh_label in BEARISH:
        return "✅ Concordano"
    return "⚠️ Discordano"


# ─── Recupero dati ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_yahoo_data(ticker: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "current_price": None,
        "yahoo_rating":  None,
        "target_high":   None,
        "target_low":    None,
        "target_mean":   None,
        "error":         None,
    }
    try:
        info = yf.Ticker(ticker).info
        if not info.get("symbol") and not info.get("currentPrice") and not info.get("regularMarketPrice"):
            result["error"] = "Ticker non trovato su Yahoo Finance"
            return result
        result["yahoo_rating"]  = info.get("recommendationKey")
        result["current_price"] = info.get("currentPrice") or info.get("regularMarketPrice")
        result["target_high"]   = info.get("targetHighPrice")
        result["target_low"]    = info.get("targetLowPrice")
        result["target_mean"]   = info.get("targetMeanPrice")
    except Exception as exc:
        result["error"] = str(exc)
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def get_finnhub_data(ticker: str, api_key: str) -> Dict[str, Any]:
    fh_ticker = yahoo_to_finnhub(ticker)
    result: Dict[str, Any] = {
        "fh_strong_buy":  None,
        "fh_buy":         None,
        "fh_hold":        None,
        "fh_sell":        None,
        "fh_strong_sell": None,
        "fh_total":       None,
        "fh_ticker_used": fh_ticker,
        "error":          None,
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
            result["error"] = "API Key non valida"
            return result
        if resp.status_code != 200:
            result["error"] = f"HTTP {resp.status_code}"
            return result
        data = resp.json()
        if not data:
            result["error"] = f"Nessun dato (cercato come '{fh_ticker}')"
            return result
        latest = data[0]
        sb  = int(latest.get("strongBuy",  0) or 0)
        b   = int(latest.get("buy",        0) or 0)
        h   = int(latest.get("hold",       0) or 0)
        s   = int(latest.get("sell",       0) or 0)
        ss  = int(latest.get("strongSell", 0) or 0)
        total = sb + b + h + s + ss
        result.update({
            "fh_strong_buy":  sb,
            "fh_buy":         b,
            "fh_hold":        h,
            "fh_sell":        s,
            "fh_strong_sell": ss,
            "fh_total":       total if total > 0 else None,
        })
    except Exception as exc:
        result["error"] = str(exc)
    return result


# ─── Costruzione DataFrame ────────────────────────────────────────────────────

def build_dataframe(
    tickers: list,
    finnhub_key: str,
    progress_bar,
) -> tuple[pd.DataFrame, list[str]]:
    rows = []
    warnings = []
    n = len(tickers)

    for i, ticker in enumerate(tickers):
        progress_bar.progress(
            (i + 1) / n,
            text=f"Analisi {ticker}  ({i + 1}/{n})...",
        )
        y  = get_yahoo_data(ticker)
        fh = get_finnhub_data(ticker, finnhub_key)

        if y["error"]:
            warnings.append(f"**{ticker}** — Yahoo Finance: {y['error']}")
        if fh["error"] and finnhub_key:
            fh_t = fh["fh_ticker_used"]
            label = f" (cercato come `{fh_t}`)" if fh_t != ticker else ""
            warnings.append(f"**{ticker}**{label} — Finnhub: {fh['error']}")

        fh_total = fh["fh_total"]
        fh_sb    = fh["fh_strong_buy"]
        fh_pct: float | None = (
            round(fh_sb / fh_total * 100, 1)
            if fh_sb is not None and fh_total and fh_total > 0
            else None
        )

        price    = y["current_price"]
        tgt_mean = y["target_mean"]
        upside: float | None = (
            round((tgt_mean - price) / price * 100, 1)
            if price and tgt_mean and price > 0
            else None
        )

        yahoo_rating = y["yahoo_rating"] or "N/D"
        fh_label     = compute_fh_label(fh_sb, fh["fh_buy"], fh["fh_hold"], fh["fh_sell"], fh["fh_strong_sell"])
        accordo      = compute_accordo(yahoo_rating, fh_label)

        rows.append({
            "Ticker":         ticker,
            "ISIN":           TICKER_ISIN.get(ticker, "N/D"),
            "Prezzo (€/$)":   price,
            "Yahoo Rating":   yahoo_rating,
            "Finnhub Rating": fh_label,
            "Accordo":        accordo,
            "Upside %":       upside,
            "Target Low":     y["target_low"],
            "Target Mean":    tgt_mean,
            "Target High":    y["target_high"],
            "FH SB %":        fh_pct,
            "Analisti FH":    fh_total,
            "FH Strong Buy":  fh_sb,
            "FH Buy":         fh["fh_buy"],
            "FH Hold":        fh["fh_hold"],
            "FH Sell":        fh["fh_sell"],
            "FH Strong Sell": fh["fh_strong_sell"],
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

def _fmt_price(val) -> str:
    try:
        return f"{float(val):,.2f}" if pd.notna(val) else "N/D"
    except (TypeError, ValueError):
        return "N/D"


def _fmt_int(val) -> str:
    try:
        return str(int(val)) if pd.notna(val) else "N/D"
    except (TypeError, ValueError):
        return "N/D"


def _fmt_pct(val) -> str:
    try:
        return f"{float(val):.1f}%" if pd.notna(val) else "N/D"
    except (TypeError, ValueError):
        return "N/D"


def _fmt_upside(val) -> str:
    try:
        if pd.isna(val):
            return "N/D"
        v = float(val)
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.1f}%"
    except (TypeError, ValueError):
        return "N/D"


# Colonne mostrate nella tabella UI (le altre restano nel CSV)
DISPLAY_COLS = [
    "Ticker", "ISIN", "Prezzo (€/$)", "Yahoo Rating", "Finnhub Rating",
    "Accordo", "Upside %", "FH SB %", "Analisti FH",
]


def format_for_display(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["Yahoo Rating"]   = d["Yahoo Rating"].map(lambda x: RATING_LABEL.get(str(x).lower(), x))
    d["Finnhub Rating"] = d["Finnhub Rating"].map(
        lambda x: RATING_LABEL.get(str(x).lower(), "N/D") if x else "N/D"
    )
    d["Prezzo (€/$)"] = d["Prezzo (€/$)"].apply(_fmt_price)
    d["FH SB %"]      = d["FH SB %"].apply(_fmt_pct)
    d["Upside %"]     = d["Upside %"].apply(_fmt_upside)
    d["Analisti FH"]  = d["Analisti FH"].apply(_fmt_int)
    return d[DISPLAY_COLS]


def color_rating(val: str) -> str:
    return RATING_COLORS.get(str(val), "")


def color_upside(val: str) -> str:
    if not val or val == "N/D":
        return ""
    try:
        v = float(str(val).replace("%", "").replace("+", ""))
        if v > 0:
            return "color: #1b5e20; font-weight: bold"
        if v < 0:
            return "color: #b71c1c; font-weight: bold"
    except ValueError:
        pass
    return ""


def color_accordo(val: str) -> str:
    if val.startswith("✅"):
        return "color: #1b5e20; font-weight: bold"
    if val.startswith("⚠️"):
        return "color: #e65100; font-weight: bold"
    return "color: #757575"


def style_table(display_df: pd.DataFrame):
    return (
        display_df.style
        .map(color_rating, subset=["Yahoo Rating", "Finnhub Rating"])
        .map(color_upside,  subset=["Upside %"])
        .map(color_accordo, subset=["Accordo"])
    )


# ─── App principale ───────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Analisti BuySell",
        page_icon="📈",
        layout="wide",
    )

    st.title("📈 Analisti BuySell")
    st.markdown(
        "Confronto del consenso degli analisti: **Yahoo Finance** ↔ **Finnhub** — "
        "due fonti indipendenti a confronto per ridurre i falsi segnali."
    )

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
            help="Registrati gratis su https://finnhub.io → Dashboard → API Key",
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
            "Uno per riga o separati da virgola",
            placeholder="UBER\nSPOT, SNOW",
            height=110,
        )

        st.divider()
        run = st.button("🔍 Analizza ora", type="primary", use_container_width=True)

        if st.button("🗑️ Svuota cache dati", use_container_width=True,
                     help="Forza il riscariamento alla prossima analisi (cache 1 ora)"):
            st.cache_data.clear()
            st.toast("Cache svuotata — la prossima analisi scaricherà dati aggiornati.", icon="✅")

    # ── Lista ticker ──────────────────────────────────────────────────────────
    tickers: list = list(DEFAULT_TICKERS) if use_default else []

    if custom_raw.strip():
        for raw in custom_raw.replace(",", "\n").splitlines():
            t = raw.strip().upper()
            if t and t not in tickers:
                tickers.append(t)

    if not tickers:
        st.info("Abilita la lista predefinita oppure aggiungi ticker personalizzati.")
        return

    st.markdown(
        f"**{len(tickers)} ticker da analizzare:** "
        + "  ".join(f"`{t}`" for t in tickers)
    )

    # ── Analisi ───────────────────────────────────────────────────────────────
    if run:
        bar = st.progress(0, text="Avvio analisi...")
        df, warns = build_dataframe(tickers, finnhub_key, bar)
        bar.empty()
        st.session_state["df"]       = df
        st.session_state["warnings"] = warns
        st.success(f"✅ Analisi completata: {len(df)} titoli elaborati.")

    # ── Visualizzazione risultati ─────────────────────────────────────────────
    if "df" not in st.session_state:
        return

    df: pd.DataFrame = st.session_state["df"]
    warnings: list   = st.session_state.get("warnings", [])

    # — Legenda colonne —
    with st.expander("📖 Come leggere la tabella", expanded=False):
        st.markdown("""
| Colonna | Significato |
|---|---|
| **Yahoo Rating** | Valutazione sintetica degli analisti secondo Yahoo Finance. Va da ❌ Strong Sell (molto negativo) a ⭐ Strong Buy (molto positivo). |
| **Finnhub Rating** | Stessa scala, calcolata dalla media ponderata degli analisti su Finnhub (fonte indipendente). |
| **Accordo** | ✅ Le due fonti concordano · ⚠️ Le due fonti discordano · ❓ Dati Finnhub non disponibili |
| **Upside %** | Differenza % tra il prezzo attuale e il **Target Mean** (prezzo obiettivo medio degli analisti). Verde = potenziale di salita, rosso = sopravvalutato. |
| **FH SB %** | Percentuale di analisti Finnhub che hanno assegnato il massimo rating "Strong Buy". Più alto = maggiore convinzione rialzista. |
| **Analisti FH** | Numero totale di analisti che coprono il titolo su Finnhub. Più è alto, più la valutazione è affidabile. |
        """)

    # — Avvisi fetch —
    if warnings:
        with st.expander(f"⚠️ {len(warnings)} avvisi tecnici (espandi per dettagli)", expanded=False):
            for w in warnings:
                st.markdown(f"- {w}")

    # — Sezione Consenso Assoluto —
    mask  = df.apply(is_consenso_assoluto, axis=1)
    df_ca = df[mask].reset_index(drop=True)

    st.divider()
    col_h1, col_h2 = st.columns([3, 1])
    col_h1.subheader("⭐ Consenso Assoluto")
    col_h2.metric("Titoli trovati", len(df_ca))

    st.caption(
        "Titoli in cui **entrambe le fonti** sono fortemente d'accordo: "
        "Yahoo Finance = **Strong Buy** e più del **50%** degli analisti Finnhub "
        "ha assegnato il rating massimo. Il filtro doppio riduce i falsi segnali."
    )

    if df_ca.empty:
        st.info("Nessun titolo soddisfa entrambi i criteri in questo momento.")
    else:
        st.dataframe(style_table(format_for_display(df_ca)), use_container_width=True, hide_index=True)

    # — Tabella completa —
    st.divider()
    st.subheader("📊 Tutti i titoli analizzati")
    st.caption(
        "Ordinati per: 1° Yahoo Rating · 2° FH Strong Buy %. "
        "Clicca un'intestazione di colonna per riordinare."
    )

    st.dataframe(style_table(format_for_display(df)), use_container_width=True, hide_index=True)

    st.download_button(
        label="⬇️ Scarica CSV completo",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="analisti_buysell.csv",
        mime="text/csv",
        help="Il CSV include anche i dati dettagliati Finnhub (Strong Buy, Buy, Hold, Sell, Strong Sell).",
    )


if __name__ == "__main__":
    main()
