"""Scarica 5 anni di chiusure e volumi per tutto l'universo ampio, a blocchi.

Uso: python studio/prezzi_ampi.py              (5 anni -> data/prezzi_ampi.parquet e data/volumi_ampi.parquet)
     python studio/prezzi_ampi.py --anni 15    (storia lunga per piano.py --lungo -> data/prezzi_lunghi.parquet e
                                                volumi_lunghi.parquet; include SPY e i titoli già in prezzi_ampi)
Scrive .csv.gz se manca pyarrow.
"""

import sys
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


def main(anni: int = ANNI_STORICO, nome: str = "ampi") -> None:
    tickers = pd.read_csv(FILE_UNIVERSO_AMPIO)["Symbol"].tolist()
    vecchi = esistenti()
    if nome != "ampi":      # archivio lungo: stessi titoli dell'archivio corrente, più SPY per il confronto
        tickers = sorted(set(tickers) | set(vecchi[0].columns if vecchi else []) | {"SPY"})
        vecchi = None
    inizio = (date.today() - timedelta(days=365 * anni + 30)).isoformat()
    chiusure, volumi = [], []
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
    print(f"Chiusure: {close.shape[0]} giorni x {close.shape[1]} titoli -> {salva(close, f'prezzi_{nome}')}")
    print(f"Volumi -> {salva(vol, f'volumi_{nome}')}")


if __name__ == "__main__":
    if "--anni" in sys.argv:
        main(int(sys.argv[sys.argv.index("--anni") + 1]), "lunghi")
    else:
        main()
