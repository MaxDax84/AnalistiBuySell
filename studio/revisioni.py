"""Revisioni degli utili attesi: gli analisti stanno alzando o abbassando le stime di utile per azione?

Uso: python studio/revisioni.py MU ASML.AS        (stampa le revisioni dei titoli indicati)

Non è il giudizio "Compra/Vendi" (che lo studio ha trovato inutile): è la variazione della stima di utile, un
segnale diverso e documentato in letteratura. Yahoo dà solo la fotografia di oggi (stima attuale e di 7, 30, 60,
90 giorni fa), quindi NON si può fare un backtest: carta.py salva la fotografia dei candidati ogni sera in
data/revisioni/AAAA-MM-GG.csv, e tra qualche mese lo storico raccolto permetterà di misurarlo.
"""
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import yfinance as yf

from config import DATI

DIR_REVISIONI = DATI / "revisioni"
PERIODI = ["+1y", "0y"]      # anno prossimo, poi anno in corso


def una(ticker: str) -> dict | None:
    try:
        t = yf.Ticker(ticker).eps_trend
        for p in PERIODI:
            if p in t.index and pd.notna(t.loc[p, "current"]) and pd.notna(t.loc[p, "30daysAgo"]) and t.loc[p, "30daysAgo"] != 0:
                r = t.loc[p]
                return {"Ticker": ticker, "periodo": p, "attuale": r["current"], "7gg_fa": r["7daysAgo"], "30gg_fa": r["30daysAgo"],
                        "60gg_fa": r["60daysAgo"], "90gg_fa": r["90daysAgo"],
                        "revisione_30gg_%": 100 * (r["current"] - r["30daysAgo"]) / abs(r["30daysAgo"])}
    except Exception:
        pass
    return None


def raccogli(tickers: list[str], data: str) -> dict[str, float]:
    """Scarica (o rilegge) le revisioni del giorno. Ritorna {ticker: revisione a 30 giorni in %}; chi manca non ha stime."""
    DIR_REVISIONI.mkdir(parents=True, exist_ok=True)
    percorso = DIR_REVISIONI / f"{data}.csv"
    tab = pd.read_csv(percorso) if percorso.exists() else pd.DataFrame(columns=["Ticker"])
    mancanti = [t for t in tickers if t not in set(tab["Ticker"])]
    if mancanti:
        with ThreadPoolExecutor(4) as pool:
            nuove = [r for r in pool.map(una, mancanti) if r]
        senza = [{"Ticker": t} for t in mancanti if t not in {r["Ticker"] for r in nuove}]     # segnati per non richiederli
        tab = pd.concat([tab, pd.DataFrame(nuove + senza)], ignore_index=True)
        tab.to_csv(percorso, index=False)
    if "revisione_30gg_%" not in tab:
        return {}
    return tab.dropna(subset=["revisione_30gg_%"]).set_index("Ticker")["revisione_30gg_%"].to_dict()


if __name__ == "__main__":
    for t in sys.argv[1:]:
        print(una(t))
