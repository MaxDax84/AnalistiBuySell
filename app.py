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
    # European
    "ASML", "MC.PA", "VOW3.DE", "SAP.DE",
    # Italiani (formato Yahoo Finance — suffisso .MI per Borsa di Milano)
    "RACE", "ENI.MI", "STLAM.MI", "UCG.MI", "ISP.MI",
]

RATING_RANK: Dict[str, int] = {
    "strong_buy":   5,
    "buy":          4,
    "hold":         3,
    "underperform": 2,
    "sell":         1,
    "strong_sell":  0,
}

RATING_COLORS: Dict[str, str] = {
    "strong_buy":   "background-color: #1b5e20; color: white",
    "buy":          "background-color: #388e3c; color: white",
    "hold":         "background-color: #f57c00; color: black",
    "underperform": "background-color: #e53935; color: white",
    "sell":         "background-color: #b71c1c; color: white",
    "strong_sell":  "background-color: #4a148c; color: white",
}


# ─── Recupero dati ────────────────────────────────────────────────────────────

def get_yahoo_data(ticker: str) -> Dict[str, Any]:
    """Scarica raccomandazione e target di prezzo da Yahoo Finance."""
    result: Dict[str, Any] = {
        "current_price": None,
        "yahoo_rating":  None,
        "target_high":   None,
        "target_low":    None,
        "target_mean":   None,
    }
    try:
        info = yf.Ticker(ticker).info
        result["yahoo_rating"]  = info.get("recommendationKey")
        result["current_price"] = (
            info.get("currentPrice") or info.get("regularMarketPrice")
        )
        result["target_high"] = info.get("targetHighPrice")
        result["target_low"]  = info.get("targetLowPrice")
        result["target_mean"] = info.get("targetMeanPrice")
    except Exception:
        pass
    return result


def get_finnhub_data(ticker: str, api_key: str) -> Dict[str, Any]:
    """Scarica il trend di raccomandazione da Finnhub (/stock/recommendation)."""
    result: Dict[str, Any] = {
        "fh_strong_buy":  None,
        "fh_buy":         None,
        "fh_hold":        None,
        "fh_sell":        None,
        "fh_strong_sell": None,
        "fh_total":       None,
    }
    if not api_key:
        return result
    try:
        resp = requests.get(
            "https://finnhub.io/api/v1/stock/recommendation",
            params={"symbol": ticker, "token": api_key},
            timeout=10,
        )
        if resp.status_code != 200:
            return result
        data = resp.json()
        if not data:
            return result
        latest = data[0]  # periodo più recente disponibile
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
    except Exception:
        pass
    return result


# ─── Costruzione DataFrame ────────────────────────────────────────────────────

def build_dataframe(
    tickers: list,
    finnhub_key: str,
    progress_bar,
) -> pd.DataFrame:
    """Raccoglie dati per ogni ticker e restituisce un DataFrame ordinato."""
    rows = []
    n = len(tickers)

    for i, ticker in enumerate(tickers):
        progress_bar.progress(
            (i + 1) / n,
            text=f"⏳  Analisi {ticker}  ({i + 1}/{n})...",
        )
        y  = get_yahoo_data(ticker)
        fh = get_finnhub_data(ticker, finnhub_key)

        fh_total = fh["fh_total"]
        fh_sb    = fh["fh_strong_buy"]
        fh_pct: float | None = (
            round(fh_sb / fh_total * 100, 1)
            if fh_sb is not None and fh_total and fh_total > 0
            else None
        )

        rows.append({
            "Ticker":         ticker,
            "Prezzo (€/$)":   y["current_price"],
            "Yahoo Rating":   y["yahoo_rating"] or "N/D",
            "Target Low":     y["target_low"],
            "Target Mean":    y["target_mean"],
            "Target High":    y["target_high"],
            "FH Strong Buy":  fh_sb,
            "FH Buy":         fh["fh_buy"],
            "FH Hold":        fh["fh_hold"],
            "FH Sell":        fh["fh_sell"],
            "FH Strong Sell": fh["fh_strong_sell"],
            "FH Totale":      fh_total,
            "FH SB %":        fh_pct,
        })

    df = pd.DataFrame(rows)

    # Ordinamento primario: rank Yahoo Rating  |  secondario: % Strong Buy Finnhub
    df["_rank"]    = df["Yahoo Rating"].map(lambda x: RATING_RANK.get(x, -1))
    df["_fh_sort"] = df["FH SB %"].fillna(0.0)
    df = (
        df.sort_values(["_rank", "_fh_sort"], ascending=[False, False])
          .drop(columns=["_rank", "_fh_sort"])
          .reset_index(drop=True)
    )
    return df


# ─── Logica Consenso Assoluto ─────────────────────────────────────────────────

def is_consenso_assoluto(row: pd.Series) -> bool:
    """
    Logica applicata (maggioranza assoluta su Finnhub):
      • Yahoo Finance → recommendationKey == 'strong_buy'
      • Finnhub       → Strong Buy > 50 % del totale analisti Finnhub

    La logica è volutamente conservativa: richiede entrambe le condizioni
    e scarta i titoli privi di dati Finnhub (FH SB % = N/D).
    """
    yahoo_ok = row["Yahoo Rating"] == "strong_buy"
    fh_pct   = row.get("FH SB %")
    fh_ok    = fh_pct is not None and pd.notna(fh_pct) and float(fh_pct) > 50.0
    return bool(yahoo_ok and fh_ok)


# ─── Formattazione per la visualizzazione ────────────────────────────────────

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


def format_for_display(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for col in ["Prezzo (€/$)", "Target Low", "Target Mean", "Target High"]:
        d[col] = d[col].apply(_fmt_price)
    for col in ["FH Strong Buy", "FH Buy", "FH Hold", "FH Sell", "FH Strong Sell", "FH Totale"]:
        d[col] = d[col].apply(_fmt_int)
    d["FH SB %"] = d["FH SB %"].apply(_fmt_pct)
    return d


def color_rating(val: str) -> str:
    return RATING_COLORS.get(str(val).lower(), "")


# ─── App principale ───────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="Analisti BuySell",
        page_icon="📈",
        layout="wide",
    )

    st.title("📈 Analisti BuySell")
    st.markdown(
        "Confronto del consenso degli analisti: **Yahoo Finance** ↔ **Finnhub**"
    )

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Configurazione")

        finnhub_key: str = st.text_input(
            "🔑 Finnhub API Key",
            type="password",
            placeholder="Incolla qui la tua API Key...",
            help="Registrati gratis su https://finnhub.io → Dashboard → API Key",
        )
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
        df  = build_dataframe(tickers, finnhub_key, bar)
        bar.empty()
        st.session_state["df"] = df
        st.success(f"✅ Analisi completata: {len(df)} titoli elaborati.")

    # ── Visualizzazione risultati ─────────────────────────────────────────────
    if "df" not in st.session_state:
        return

    df: pd.DataFrame = st.session_state["df"]

    # — Sezione Consenso Assoluto —
    mask  = df.apply(is_consenso_assoluto, axis=1)
    df_ca = df[mask].reset_index(drop=True)

    st.divider()
    col_h1, col_h2 = st.columns([3, 1])
    col_h1.subheader("⭐ Consenso Assoluto")
    col_h2.metric("Titoli trovati", len(df_ca))

    st.caption(
        "**Criteri (entrambi obbligatori):** "
        "Yahoo Rating = `strong_buy` "
        "**e** FH Strong Buy > 50 % del totale analisti Finnhub."
    )

    if df_ca.empty:
        st.info("Nessun titolo soddisfa entrambi i criteri in questo momento.")
    else:
        ca_display = format_for_display(df_ca)
        ca_styled  = ca_display.style.map(color_rating, subset=["Yahoo Rating"])
        st.dataframe(ca_styled, use_container_width=True, hide_index=True)

    # — Tabella completa —
    st.divider()
    st.subheader("📊 Tabella Completa di Confronto")
    st.caption(
        "Ordinata per: 1° Yahoo Rating (decrescente) · 2° FH Strong Buy % (decrescente)"
    )

    full_display = format_for_display(df)
    full_styled  = full_display.style.map(color_rating, subset=["Yahoo Rating"])
    st.dataframe(full_styled, use_container_width=True, hide_index=True)

    st.download_button(
        label="⬇️ Scarica CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="analisti_buysell.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
