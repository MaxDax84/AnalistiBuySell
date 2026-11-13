"""Ricostruisce il consenso degli analisti giorno per giorno a partire dalle singole azioni delle banche.

Ogni banca ha un giudizio corrente per ogni titolo (l'ultimo che ha dato, valido 12 mesi).
Il consenso del giorno è la media dei giudizi correnti, su una scala 1 (Strong Sell) - 5 (Strong Buy).
Si chiama "point-in-time": usa solo ciò che era noto quel giorno, mai correzioni successive.
"""

import pandas as pd

from config import MESI_VALIDITA_GIUDIZIO

# Giudizio -> punteggio 1..5. I nomi cambiano da banca a banca, il significato no.
PUNTEGGI = {
    5: {"strong buy", "conviction buy", "top pick", "strong-buy", "buy (strong)", "focus list"},
    4: {"buy", "outperform", "overweight", "positive", "accumulate", "add", "long-term buy",
        "sector outperform", "market outperform", "speculative buy", "moderate buy", "attractive",
        "outperformer", "above average", "recommended list", "action list buy", "gradually accumulate",
        "trading buy", "conviction list", "overperform", "top idea"},
    3: {"hold", "neutral", "equal-weight", "equalweight", "equal weight", "market perform",
        "sector perform", "in-line", "inline", "in line", "peer perform", "perform", "sector weight",
        "market weight", "fair value", "mixed", "average", "perform-in-line", "fairly valued",
        "equal-weight/attractive", "equal-weight/cautious", "cautious", "no rating", "not rated",
        "sector performer", "market performer", "hold neutral", "maintain", "balanced"},
    2: {"underperform", "underweight", "reduce", "negative", "sector underperform", "market underperform",
        "below average", "moderate sell", "trim", "unattractive", "underperformer", "lighten"},
    1: {"sell", "strong sell", "conviction sell", "strong-sell", "sell (strong)"},
}
_MAPPA = {nome: punti for punti, nomi in PUNTEGGI.items() for nome in nomi}


def punteggio(giudizio) -> float | None:
    if not isinstance(giudizio, str):
        return None
    return _MAPPA.get(giudizio.strip().lower())


def giudizi_non_mappati(azioni: pd.DataFrame) -> pd.Series:
    """Giudizi che compaiono nei dati ma non hanno un punteggio: da aggiungere a PUNTEGGI."""
    tutti = pd.concat([azioni["ToGrade"], azioni["FromGrade"]]).dropna()
    tutti = tutti[tutti.str.strip() != ""]
    conteggi = tutti.value_counts()
    return conteggi[[punteggio(g) is None for g in conteggi.index]]


def etichetta(score: float) -> str:
    if pd.isna(score):
        return "n/d"
    if score >= 4.0:
        return "Compra"
    if score < 3.0:
        return "Vendi"
    return "Tieni"


def consenso_giornaliero(azioni: pd.DataFrame, giorni_borsa: pd.DatetimeIndex) -> pd.DataFrame:
    """Per ogni titolo e giorno di borsa: punteggio medio, numero di banche, etichetta.

    Un'azione annunciata nel giorno D (anche a mercato aperto) conta dalla chiusura di D:
    chi la segue compra alla chiusura di D e il rendimento parte da lì.
    """
    az = azioni.copy()
    az["punti"] = az["ToGrade"].map(punteggio)
    az = az.dropna(subset=["punti", "Firm"])
    # data del segnale = primo giorno di borsa uguale o successivo alla data dell'azione
    date_azione = az["Data"].dt.normalize()
    posizioni = giorni_borsa.searchsorted(date_azione.values, side="left")
    valide = posizioni < len(giorni_borsa)
    az = az[valide].copy()
    az["Giorno"] = giorni_borsa[posizioni[valide]]

    limite = int(MESI_VALIDITA_GIUDIZIO * 21)
    pezzi = []
    for ticker, gruppo in az.groupby("Ticker", sort=False):
        # per banca e giorno tieni l'ultimo giudizio, poi propaga nel tempo (al massimo 12 mesi)
        tab = (gruppo.sort_values("Data").groupby(["Giorno", "Firm"])["punti"].last()
               .unstack("Firm").reindex(giorni_borsa).ffill(limit=limite))
        pezzi.append(pd.DataFrame({
            "Ticker": ticker,
            "Data": giorni_borsa,
            "score": tab.mean(axis=1).values,
            "n_banche": tab.notna().sum(axis=1).values,
        }))
    cons = pd.concat(pezzi, ignore_index=True).dropna(subset=["score"])
    cons["etichetta"] = cons["score"].map(etichetta)
    return cons


def eventi(azioni: pd.DataFrame, consenso: pd.DataFrame) -> pd.DataFrame:
    """Due famiglie di segnali, con la data del giorno di borsa in cui si agisce.

    - banca: una singola banca alza (up), abbassa (down) o avvia (init) il giudizio
    - consenso: l'etichetta del consenso cambia (es. Tieni -> Compra)
    """
    az = azioni.copy()
    az["a"] = az["ToGrade"].map(punteggio)
    az["da"] = az["FromGrade"].map(punteggio)
    giorni = pd.DatetimeIndex(sorted(consenso["Data"].unique()))
    pos = giorni.searchsorted(az["Data"].dt.normalize().values, side="left")
    ok = pos < len(giorni)
    az = az[ok].copy()
    az["Data_segnale"] = giorni[pos[ok]]

    banca = az.dropna(subset=["a"]).copy()
    # fidati dell'Action di Yahoo ma correggila con i punteggi quando sono entrambi noti
    banca["tipo"] = banca["Action"].map({"up": "banca: alza", "down": "banca: abbassa", "init": "banca: avvia"})
    noti = banca["da"].notna()
    banca.loc[noti & (banca["a"] > banca["da"]), "tipo"] = "banca: alza"
    banca.loc[noti & (banca["a"] < banca["da"]), "tipo"] = "banca: abbassa"
    banca.loc[noti & (banca["a"] == banca["da"]) & banca["Action"].isin(["up", "down"]), "tipo"] = None
    banca = banca.dropna(subset=["tipo"])[["Ticker", "Data_segnale", "tipo"]]
    # più banche lo stesso giorno sullo stesso titolo = un solo segnale
    banca = banca.drop_duplicates()

    cons = consenso.sort_values(["Ticker", "Data"]).copy()
    cons["prima"] = cons.groupby("Ticker")["etichetta"].shift()
    cambi = cons[cons["prima"].notna() & (cons["prima"] != cons["etichetta"])]
    cambi = cambi.rename(columns={"Data": "Data_segnale"})
    cambi["tipo"] = "consenso: " + cambi["prima"] + " -> " + cambi["etichetta"]
    cambi = cambi[["Ticker", "Data_segnale", "tipo"]]

    return pd.concat([banca, cambi], ignore_index=True)
