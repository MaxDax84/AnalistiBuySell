"""Fotografia giornaliera del consenso: una riga per titolo con il giudizio di oggi e il prezzo.

Uso: python studio/giornaliero.py
Scrive data/giornaliero/AAAA-MM-GG.csv. Pensato per girare ogni sera da GitHub Actions:
dopo due mesi si confronta il giudizio del giorno X con i prezzi dei giorni successivi
senza il rischio che lo storico sia stato corretto a posteriori.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pandas as pd
import requests
import yfinance as yf

from config import DATI_GIORNALIERI, FILE_UNIVERSO, chiave_finnhub


def fotografia_yahoo(simbolo: str) -> dict:
    riga = {"Ticker": simbolo}
    try:
        t = yf.Ticker(simbolo)
        info = t.info or {}
        riga.update({
            "prezzo": info.get("currentPrice") or info.get("regularMarketPrice"),
            "yahoo_rating": info.get("recommendationKey"),
            "yahoo_media": info.get("recommendationMean"),
            "n_analisti": info.get("numberOfAnalystOpinions"),
            "target_medio": info.get("targetMeanPrice"),
        })
        rec = t.recommendations
        if rec is not None and not rec.empty:
            oggi = rec.iloc[0]
            for col in ("strongBuy", "buy", "hold", "sell", "strongSell"):
                riga[f"y_{col}"] = int(oggi.get(col, 0) or 0)
    except Exception as err:
        riga["errore"] = str(err)[:80]
    return riga


def fotografia_finnhub(tickers: list[str], chiave: str) -> dict[str, dict]:
    esito = {}
    for n, simbolo in enumerate(tickers, 1):
        try:
            r = requests.get("https://finnhub.io/api/v1/stock/recommendation",
                             params={"symbol": simbolo, "token": chiave}, timeout=20)
            if r.status_code == 401:
                print("Finnhub: chiave non valida, salto")
                return {}
            if r.status_code == 429:
                time.sleep(60)
                continue
            mesi = r.json() or []
            if mesi:
                ultimo = mesi[0]
                esito[simbolo] = {f"fh_{k}": ultimo.get(k) for k in
                                  ("strongBuy", "buy", "hold", "sell", "strongSell", "period")}
        except Exception:
            pass
        if n % 55 == 0:
            time.sleep(61)
    return esito


def main() -> None:
    DATI_GIORNALIERI.mkdir(parents=True, exist_ok=True)
    tickers = pd.read_csv(FILE_UNIVERSO)["Symbol"].tolist()
    oggi = date.today().isoformat()

    with ThreadPoolExecutor(max_workers=6) as pool:
        righe = list(pool.map(fotografia_yahoo, tickers))
    tab = pd.DataFrame(righe)
    tab.insert(0, "data", oggi)

    chiave = chiave_finnhub()
    if chiave:
        fh = fotografia_finnhub(tickers, chiave)
        if fh:
            tab = tab.merge(pd.DataFrame.from_dict(fh, orient="index").rename_axis("Ticker").reset_index(),
                            on="Ticker", how="left")

    destinazione = DATI_GIORNALIERI / f"{oggi}.csv"
    tab.to_csv(destinazione, index=False)
    ok = tab["yahoo_rating"].notna().sum() if "yahoo_rating" in tab else 0
    print(f"{destinazione.name}: {len(tab)} titoli, {ok} con giudizio Yahoo"
          + (f", {len(fh)} con Finnhub" if chiave and fh else ""))


if __name__ == "__main__":
    main()
