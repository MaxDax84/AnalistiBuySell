"""Varianti della regola di scelta dei titoli, da confrontare nel backtest (piano.py --modelli) e su carta (carta.py).

Ogni modello è un dizionario di opzioni; quelle non indicate valgono come nella regola di partenza ("base"):
  universo   "oggi"  = europei + USA che OGGI valgono più di 1 mld $ (chi è salito è dentro: gonfia il momentum)
             "data"  = tutti i titoli scaricati; la dimensione si giudica con gli scambi di QUEL giorno
                       (controvalore mediano 20 gg > 5 M$). Restano fuori solo i titoli spariti dal listino.
  segnale    "tetto"   = momentum 12-1 in punteggio standard con tetto a ±3 (i migliori finiscono alla pari)
             "rango"   = stesso momentum, ma in graduatoria dentro il proprio mercato: nessun pari merito
             "pulito"  = rendimento medio diviso oscillazione negli stessi 11 mesi: premia chi è salito con
                         regolarità, non chi ha fatto +300% in un giorno per una notizia
  corr_max   None oppure il massimo di correlazione (rendimenti giornalieri, 6 mesi) ammesso tra un nuovo acquisto
             e i titoli già scelti: evita tre petroliferi insieme. Se non ci sono abbastanza candidati, si completa
             con i migliori rimasti.
  freno      True = nessun nuovo acquisto nei giorni in cui il verdetto di mercato è SMALL SELL (verdetto.py);
             la cassa aspetta. È il momento in cui il momentum storicamente perde di più.
  vol_max    volatilità annua massima dei candidati (0,50 = filtro "prudente"; None = nessun filtro)
  utili      True = (solo su carta) compra solo titoli con utili attesi rivisti al rialzo negli ultimi 30 giorni
"""
import numpy as np
import pandas as pd

from classifica import fattori, punteggi
from prezzi_ampi import carica
from universo_ampio import FILE_UNIVERSO_AMPIO, simboli_classifica

CONTROVALORE_DATA = 5e6      # $ al giorno alla data: sostituisce "capitalizzazione di oggi > 1 mld $"
FINESTRA_CORR = 120
BASE = {"universo": "oggi", "segnale": "tetto", "corr_max": None, "freno": False, "vol_max": 0.50, "utili": False}

MODELLI = {
    "base": {},
    "senza pari merito": {"segnale": "rango"},
    "universo alla data": {"universo": "data", "segnale": "rango"},
    "+ momentum pulito": {"universo": "data", "segnale": "pulito"},
    "+ no titoli gemelli": {"universo": "data", "segnale": "rango", "corr_max": 0.5},
    "+ freno di mercato": {"universo": "data", "segnale": "rango", "freno": True},
    "pulito + no gemelli": {"universo": "data", "segnale": "pulito", "corr_max": 0.5},
    "tutto insieme": {"universo": "data", "segnale": "pulito", "corr_max": 0.5, "freno": True},
    "tutto, senza filtro volatilità": {"universo": "data", "segnale": "pulito", "corr_max": 0.5, "freno": True, "vol_max": None},
}


def opzioni(modello: dict) -> dict:
    return {**BASE, **modello}


def rango_per_mercato(tab: pd.DataFrame, ammesso: pd.DataFrame, mercato: pd.Series) -> pd.DataFrame:
    """Posizione in graduatoria (0-1) rispetto ai titoli ammessi dello stesso mercato nello stesso giorno."""
    t = tab.where(ammesso)
    pezzi = [t[mercato.index[mercato == m]].rank(axis=1, pct=True) for m in mercato.unique()]
    return pd.concat(pezzi, axis=1)[t.columns]


_cache: dict = {}


def dati(universo: str) -> dict:
    """Prezzi, fattori e ammissione per un universo. Ritorna un dizionario riusato da tutti i modelli."""
    if universo in _cache:
        return _cache[universo]
    close, vol = carica("prezzi_ampi"), carica("volumi_ampi")
    info = pd.read_csv(FILE_UNIVERSO_AMPIO)
    if universo == "oggi":
        tieni = [c for c in close.columns if c in simboli_classifica(info)]
        close, vol = close[tieni], vol[tieni]
    close = close.ffill(limit=3)
    f = fattori(close, vol, info)
    if universo == "data":
        f["ammesso"] = f["ammesso"] & (f["controvalore"] > CONTROVALORE_DATA)
    r = close.pct_change(fill_method=None)
    d = {"close": close, "info": info, "f": f, "r": r, "punteggi": {}}
    _cache[universo] = d
    return d


def punteggio(d: dict, segnale: str) -> pd.DataFrame:
    if segnale in d["punteggi"]:
        return d["punteggi"][segnale]
    f = d["f"]
    if segnale == "tetto":
        s, _ = punteggi(f)
    elif segnale == "rango":
        s = rango_per_mercato(f["mom_12_1"], f["ammesso"], f["mercato"])
    elif segnale == "pulito":
        passato = d["r"].shift(21)      # stessi 11 mesi del momentum 12-1: da 12 mesi fa a 1 mese fa
        regolare = passato.rolling(231, min_periods=200).mean() / passato.rolling(231, min_periods=200).std()
        s = rango_per_mercato(regolare, f["ammesso"], f["mercato"])
    else:
        raise ValueError(segnale)
    d["punteggi"][segnale] = s
    return s


def freno_mercato(date: pd.DatetimeIndex) -> np.ndarray:
    """True nei giorni in cui il verdetto di mercato è SMALL SELL (noto alla chiusura di quel giorno)."""
    from regime import FILE_REGIME, segnali
    from verdetto import verdetti
    s = segnali(pd.read_csv(FILE_REGIME, index_col=0, parse_dates=True))
    v = verdetti(s)
    return v.reindex(date, method="ffill").eq("SMALL SELL").values


def scegli(candidati: list[int], gia_scelti: list[int], posti: int, R: np.ndarray | None, t: int, corr_max: float | None) -> list[int]:
    """Dai candidati (in ordine di punteggio) prende i primi `posti` che non si muovono insieme a quelli già scelti."""
    if corr_max is None or R is None:
        return list(candidati[:posti])
    finestra = R[max(t - FINESTRA_CORR + 1, 0):t + 1]
    presi, scartati = [], []
    for j in candidati:
        if len(presi) == posti:
            break
        gemello = False
        for k in list(gia_scelti) + presi:
            a, b = finestra[:, j], finestra[:, k]
            ok = np.isfinite(a) & np.isfinite(b)
            if ok.sum() >= 40 and np.corrcoef(a[ok], b[ok])[0, 1] > corr_max:
                gemello = True
                break
        (scartati if gemello else presi).append(j)
    return presi + scartati[:posti - len(presi)]
