"""Scarica 5 anni di chiusure e volumi per tutto l'universo ampio, a blocchi.

Uso: python studio/prezzi_ampi.py
Scrive data/prezzi_ampi.parquet e data/volumi_ampi.parquet (o .csv.gz se manca pyarrow).
"""

import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from config import ANNI_STORICO, DATI
from universo_ampio import FILE_UNIVERSO_AMPIO

BLOCCO = 300


def salva(tab: pd.DataFrame, nome: str) -> str:
    try:
        percorso = DATI / f"{nome}.parquet"
        tab.to_parquet(percorso)
    except Exception:
        percorso = DATI / f"{nome}.csv.gz"
        tab.to_csv(percorso)
    return str(percorso)


def carica(nome: str) -> pd.DataFrame:
    p = DATI / f"{nome}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    return pd.read_csv(DATI / f"{nome}.csv.gz", index_col=0, parse_dates=True)


def esistenti() -> tuple[pd.DataFrame, pd.DataFrame] | None:
    try:
        return carica("prezzi_ampi"), carica("volumi_ampi")
    except Exception:
        return None


def main() -> None:
    tickers = pd.read_csv(FILE_UNIVERSO_AMPIO)["Symbol"].tolist()
    inizio = (date.today() - timedelta(days=365 * ANNI_STORICO + 30)).isoformat()
    chiusure, volumi = [], []
    vecchi = esistenti()
    if vecchi is not None and vecchi[0].index[-1] >= pd.Timestamp(date.today() - timedelta(days=4)):
        # archivio recente: scarico solo i titoli che mancano (es. europei appena aggiunti)
        mancanti = [t for t in tickers if t not in vecchi[0].columns]
        print(f"Archivio aggiornato al {vecchi[0].index[-1]:%Y-%m-%d}: scarico solo {len(mancanti)} titoli nuovi")
        chiusure.append(vecchi[0])
        volumi.append(vecchi[1])
        tickers = mancanti
        if not tickers:
            print("Niente da scaricare")
            return
    t0 = time.time()
    for i in range(0, len(tickers), BLOCCO):
        blocco = tickers[i:i + BLOCCO]
        for tentativo in range(3):
            try:
                d = yf.download(blocco, start=inizio, auto_adjust=True, progress=False, threads=True)
                break
            except Exception as err:
                print(f"  blocco {i // BLOCCO + 1}: errore {err}, riprovo")
                time.sleep(10)
        else:
            continue
        chiusure.append(d["Close"])
        volumi.append(d["Volume"])
        print(f"  {min(i + BLOCCO, len(tickers))}/{len(tickers)} titoli, {time.time() - t0:.0f} s")
    for lista in (chiusure, volumi):
        for i, tab in enumerate(lista):
            tab.index = pd.to_datetime(tab.index).tz_localize(None).normalize()
            lista[i] = tab.loc[:, ~tab.columns.duplicated()]
    close = pd.concat(chiusure, axis=1).sort_index()
    vol = pd.concat(volumi, axis=1).reindex(close.index)
    close, vol = close.loc[:, ~close.columns.duplicated()], vol.loc[:, ~vol.columns.duplicated()]
    # tieni solo i titoli con almeno un anno di storia
    ok = close.notna().sum() >= 252
    close, vol = close.loc[:, ok], vol.loc[:, ok]
    print(f"Chiusure: {close.shape[0]} giorni x {close.shape[1]} titoli -> {salva(close, 'prezzi_ampi')}")
    print(f"Volumi -> {salva(vol, 'volumi_ampi')}")


if __name__ == "__main__":
    main()
