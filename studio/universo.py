"""Costruisce l'universo: i primi N titoli dell'S&P 500 per capitalizzazione.

Uso: python studio/universo.py
Scrive data/universo.csv (Symbol, Security, GICS Sector, market_cap).
"""

import io
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
import yfinance as yf

from config import DATI, FILE_UNIVERSO, N_TITOLI, ticker_yahoo

WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def lista_sp500() -> pd.DataFrame:
    html = requests.get(WIKI, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
    tab = pd.read_html(io.StringIO(html))[0]
    tab = tab[["Symbol", "Security", "GICS Sector"]].copy()
    tab["Symbol"] = tab["Symbol"].map(ticker_yahoo)
    return tab


def capitalizzazione(simbolo: str) -> float | None:
    try:
        return yf.Ticker(simbolo).fast_info.get("marketCap")
    except Exception:
        return None


def main() -> None:
    DATI.mkdir(parents=True, exist_ok=True)
    tab = lista_sp500()
    print(f"S&P 500: {len(tab)} simboli, leggo la capitalizzazione...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        tab["market_cap"] = list(pool.map(capitalizzazione, tab["Symbol"]))
    mancanti = tab["market_cap"].isna().sum()
    tab = tab.dropna(subset=["market_cap"]).sort_values("market_cap", ascending=False).head(N_TITOLI)
    tab.to_csv(FILE_UNIVERSO, index=False)
    print(f"Scritto {FILE_UNIVERSO}: {len(tab)} titoli ({mancanti} senza capitalizzazione, esclusi)")
    print(tab.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
