"""Scarica lo storico: prezzi (Yahoo), azioni degli analisti (Yahoo), consenso mensile (Finnhub, facoltativo).

Uso: python studio/raccolta.py
Richiede data/universo.csv (vedi universo.py). Scrive in data/:
  prezzi.csv            chiusure rettificate, una colonna per titolo + benchmark
  azioni_analisti.csv   una riga per ogni upgrade/downgrade/avvio/conferma di ogni banca
  consenso_finnhub.csv  consenso mensile Finnhub (solo se la chiave è valida)
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pandas as pd
import requests
import yfinance as yf

from config import (ANNI_STORICO, BENCHMARK, DATI, FILE_AZIONI, FILE_FINNHUB, FILE_PREZZI, FILE_SPLIT,
                    FILE_UNIVERSO, chiave_finnhub)


def scarica_prezzi(tickers: list[str]) -> pd.DataFrame:
    inizio = date.today() - timedelta(days=365 * ANNI_STORICO + 30)
    dati = yf.download(tickers + [BENCHMARK], start=inizio.isoformat(), auto_adjust=True,
                       progress=False, threads=True)
    chiusure = dati["Close"]
    chiusure.index = pd.to_datetime(chiusure.index).tz_localize(None).normalize()
    return chiusure


def azioni_di(simbolo: str) -> pd.DataFrame | None:
    """Storico upgrade/downgrade di un titolo. Riprova una volta se Yahoo risponde male."""
    for tentativo in range(2):
        try:
            tab = yf.Ticker(simbolo).upgrades_downgrades
            if tab is None or tab.empty:
                return None
            tab = tab.reset_index().rename(columns={"GradeDate": "Data"})
            tab.insert(0, "Ticker", simbolo)
            return tab
        except Exception as err:
            if tentativo == 1:
                print(f"  {simbolo}: errore {err}")
            time.sleep(2)
    return None


def scarica_azioni(tickers: list[str]) -> pd.DataFrame:
    with ThreadPoolExecutor(max_workers=6) as pool:
        pezzi = [p for p in pool.map(azioni_di, tickers) if p is not None]
    tab = pd.concat(pezzi, ignore_index=True)
    tab["Data"] = pd.to_datetime(tab["Data"]).dt.tz_localize(None)
    inizio = pd.Timestamp(date.today() - timedelta(days=365 * ANNI_STORICO + 400))  # margine per il consenso iniziale
    tab = tab[tab["Data"] >= inizio].sort_values(["Ticker", "Data"]).reset_index(drop=True)
    return tab


def split_di(simbolo: str) -> pd.DataFrame | None:
    try:
        s = yf.Ticker(simbolo).splits
        if s is None or s.empty:
            return None
        tab = s.rename("rapporto").reset_index().rename(columns={"Date": "Data"})
        tab.insert(0, "Ticker", simbolo)
        return tab
    except Exception:
        return None


def scarica_split(tickers: list[str]) -> pd.DataFrame:
    """Frazionamenti azionari: servono per riportare i vecchi prezzi obiettivo alla base azionaria di oggi."""
    with ThreadPoolExecutor(max_workers=6) as pool:
        pezzi = [p for p in pool.map(split_di, tickers) if p is not None]
    tab = pd.concat(pezzi, ignore_index=True) if pezzi else pd.DataFrame(columns=["Ticker", "Data", "rapporto"])
    tab["Data"] = pd.to_datetime(tab["Data"]).dt.tz_localize(None).dt.normalize()
    return tab


def scarica_finnhub(tickers: list[str], chiave: str) -> pd.DataFrame | None:
    """Consenso mensile (strongBuy/buy/hold/sell/strongSell). Piano gratuito: 60 chiamate al minuto."""
    righe = []
    for n, simbolo in enumerate(tickers, 1):
        r = requests.get("https://finnhub.io/api/v1/stock/recommendation",
                         params={"symbol": simbolo, "token": chiave}, timeout=20)
        if r.status_code == 401:
            print("Finnhub: chiave non valida, salto il consenso mensile")
            return None
        if r.status_code == 429:
            time.sleep(60)
            continue
        for mese in r.json() or []:
            mese["Ticker"] = simbolo
            righe.append(mese)
        if n % 55 == 0:
            time.sleep(61)
    return pd.DataFrame(righe)


def main() -> None:
    universo = pd.read_csv(FILE_UNIVERSO)
    tickers = universo["Symbol"].tolist()
    DATI.mkdir(parents=True, exist_ok=True)

    print(f"Prezzi di {len(tickers)} titoli + {BENCHMARK}...")
    prezzi = scarica_prezzi(tickers)
    prezzi.to_csv(FILE_PREZZI)
    print(f"  {prezzi.shape[0]} giorni x {prezzi.shape[1]} colonne -> {FILE_PREZZI}")

    print("Azioni degli analisti (upgrade/downgrade)...")
    azioni = scarica_azioni(tickers)
    azioni.to_csv(FILE_AZIONI, index=False)
    print(f"  {len(azioni)} righe, {azioni['Ticker'].nunique()} titoli -> {FILE_AZIONI}")
    print("  Azioni:", azioni["Action"].value_counts().to_dict())

    print("Frazionamenti (split)...")
    split = scarica_split(tickers)
    split.to_csv(FILE_SPLIT, index=False)
    print(f"  {len(split)} split su {split['Ticker'].nunique()} titoli -> {FILE_SPLIT}")

    chiave = chiave_finnhub()
    if chiave:
        print("Consenso mensile Finnhub...")
        fh = scarica_finnhub(tickers, chiave)
        if fh is not None:
            fh.to_csv(FILE_FINNHUB, index=False)
            print(f"  {len(fh)} righe -> {FILE_FINNHUB}")
    else:
        print("Finnhub: nessuna chiave valida, salto il consenso mensile (facoltativo)")


if __name__ == "__main__":
    main()
