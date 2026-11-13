"""Stato giornaliero di ogni titolo: tutto ciò che un investitore vedeva quel giorno dagli analisti.

Per ogni titolo e giorno di borsa:
  score, n_banche, etichetta   consenso (vedi consenso.py)
  target                       prezzo obiettivo mediano delle banche (ultimo dato da ciascuna, valido 12 mesi)
  upside_%                     quanto manca al target: target / prezzo - 1
  tendenza_20                  score di oggi - score di 20 giorni di borsa fa (consenso in salita o in discesa)
  alza_20, abbassa_20          quante banche hanno alzato / abbassato il giudizio negli ultimi 20 giorni
  target_var_20_%              variazione del target mediano negli ultimi 20 giorni

Il risultato è salvato in risultati/stato_giornaliero.csv (si rigenera se manca).
"""

import numpy as np
import pandas as pd

from config import BENCHMARK, FILE_AZIONI, FILE_PREZZI, FILE_SPLIT, MESI_VALIDITA_GIUDIZIO, RISULTATI
from consenso import consenso_giornaliero, punteggio

FILE_STATO = RISULTATI / "stato_giornaliero.csv"
FINESTRA = 20


def _giorno_segnale(az: pd.DataFrame, giorni_borsa: pd.DatetimeIndex) -> pd.DataFrame:
    pos = giorni_borsa.searchsorted(az["Data"].dt.normalize().values, side="left")
    ok = pos < len(giorni_borsa)
    az = az[ok].copy()
    az["Giorno"] = giorni_borsa[pos[ok]]
    return az


def target_rettificati(az: pd.DataFrame) -> pd.Series:
    """Riporta i target alla base azionaria di oggi: un target dato prima di uno split 10:1 va diviso per 10,
    perché i prezzi scaricati sono già rettificati per gli split."""
    fattore = pd.Series(1.0, index=az.index)
    if not FILE_SPLIT.exists():
        print("  (manca data/split.csv: i target prima di uno split restano sulla vecchia base)")
        return az["currentPriceTarget"]
    split = pd.read_csv(FILE_SPLIT, parse_dates=["Data"])
    for ticker, g in split.groupby("Ticker"):
        righe = az.index[az["Ticker"] == ticker]
        if len(righe) == 0:
            continue
        date_az = az.loc[righe, "Data"].dt.normalize()
        for _, s in g.iterrows():
            prima = righe[(date_az < s["Data"]).values]
            fattore.loc[prima] /= s["rapporto"]
    return az["currentPriceTarget"] * fattore


def target_giornaliero(azioni: pd.DataFrame, giorni_borsa: pd.DatetimeIndex) -> pd.DataFrame:
    az = azioni[azioni["currentPriceTarget"] > 0].dropna(subset=["Firm"]).copy()
    az["currentPriceTarget"] = target_rettificati(az)
    az = _giorno_segnale(az, giorni_borsa)
    limite = int(MESI_VALIDITA_GIUDIZIO * 21)
    pezzi = []
    for ticker, g in az.groupby("Ticker", sort=False):
        tab = (g.sort_values("Data").groupby(["Giorno", "Firm"])["currentPriceTarget"].last()
               .unstack("Firm").reindex(giorni_borsa).ffill(limit=limite))
        pezzi.append(pd.DataFrame({"Ticker": ticker, "Data": giorni_borsa,
                                   "target": tab.median(axis=1).values, "n_target": tab.notna().sum(axis=1).values}))
    return pd.concat(pezzi, ignore_index=True)


def conteggio_recente(azioni: pd.DataFrame, giorni_borsa: pd.DatetimeIndex) -> pd.DataFrame:
    """Numero di upgrade e downgrade (una banca che cambia davvero giudizio) negli ultimi 20 giorni di borsa."""
    az = _giorno_segnale(azioni.copy(), giorni_borsa)
    a, da = az["ToGrade"].map(punteggio), az["FromGrade"].map(punteggio)
    az["alza"] = ((az["Action"] == "up") & (da.isna() | (a > da))) | (da.notna() & (a > da))
    az["abbassa"] = ((az["Action"] == "down") & (da.isna() | (a < da))) | (da.notna() & (a < da))
    conta = az.groupby(["Ticker", "Giorno"])[["alza", "abbassa"]].sum()
    pezzi = []
    for ticker, g in conta.groupby(level="Ticker"):
        g = g.droplevel("Ticker").reindex(giorni_borsa, fill_value=0).rolling(FINESTRA, min_periods=1).sum()
        pezzi.append(pd.DataFrame({"Ticker": ticker, "Data": giorni_borsa,
                                   "alza_20": g["alza"].values.astype(int), "abbassa_20": g["abbassa"].values.astype(int)}))
    return pd.concat(pezzi, ignore_index=True)


def stato_giornaliero(ricalcola: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ritorna (stato, prezzi). Usa il file salvato se esiste."""
    prezzi = pd.read_csv(FILE_PREZZI, index_col=0, parse_dates=True).sort_index().dropna(axis=1, how="all")
    if FILE_STATO.exists() and not ricalcola:
        return pd.read_csv(FILE_STATO, parse_dates=["Data"]), prezzi

    azioni = pd.read_csv(FILE_AZIONI, parse_dates=["Data"])
    giorni = prezzi.index
    print("Calcolo lo stato giornaliero (consenso, target, tendenza)...")
    stato = consenso_giornaliero(azioni, giorni)
    stato = stato.merge(target_giornaliero(azioni, giorni), on=["Ticker", "Data"], how="left")
    stato = stato.merge(conteggio_recente(azioni, giorni), on=["Ticker", "Data"], how="left")

    chiusure = prezzi.drop(columns=[BENCHMARK]).stack().rename("prezzo").reset_index()
    chiusure.columns = ["Data", "Ticker", "prezzo"]
    stato = stato.merge(chiusure, on=["Data", "Ticker"], how="inner")
    stato["upside_%"] = 100 * (stato["target"] / stato["prezzo"] - 1)
    stato = stato.sort_values(["Ticker", "Data"])
    stato["tendenza_20"] = stato.groupby("Ticker")["score"].diff(FINESTRA)
    stato["target_var_20_%"] = 100 * stato.groupby("Ticker")["target"].pct_change(FINESTRA, fill_method=None)
    stato = stato.reset_index(drop=True)
    RISULTATI.mkdir(parents=True, exist_ok=True)
    stato.to_csv(FILE_STATO, index=False)
    return stato, prezzi


if __name__ == "__main__":
    stato, _ = stato_giornaliero(ricalcola=True)
    print(stato.describe().T[["count", "mean", "50%"]].round(2).to_string())
