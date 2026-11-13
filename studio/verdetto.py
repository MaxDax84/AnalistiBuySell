"""Verdetto del giorno: STRONG BUY / BUY / WAIT / SMALL SELL, da regole fisse verificate dal 1990.

Uso: python studio/verdetto.py            (valuta le regole su tutta la storia e stampa il verdetto di oggi)
     python studio/verdetto.py --oggi     (solo il verdetto di oggi)

Le regole, in ordine di priorità (la prima che scatta vince):
  STRONG BUY  panico o capitolazione: VIX > 30, oppure indice oltre 20% sotto il massimo di 1 anno,
              oppure HYG (credito) sceso più del 6% in 60 giorni
  SMALL SELL  allarme: 12 mesi negativi, oppure credito in stress (HYG -3/-6% in 60 gg),
              oppure indice 10-20% sotto il massimo con VIX 20-30 (il "coltello che cade")
  BUY         occasione ordinaria: indice 5-10% sotto il massimo con 12 mesi positivi e credito tranquillo,
              oppure incertezza politica estrema (EPU top 10%) con credito tranquillo
  WAIT        tutto il resto (di solito: mercato vicino ai massimi, nulla da fare)

"Small" perché i dati dicono che uscire del tutto costa rendimento: si riduce, non si vende tutto.
Il verdetto serve a decidere QUANTO investire della liquidità, non se stare o no sul mercato.
"""

import argparse

import numpy as np
import pandas as pd

from config import RISULTATI
from regime import FILE_REGIME, ORIZZONTI, decennio, lettura_oggi, md, scarica, segnali, semaforo

ORDINE = ["STRONG BUY", "BUY", "WAIT", "SMALL SELL"]


def verdetti(s: pd.DataFrame) -> pd.Series:
    vix, dd, hyg = s["VIX"], s["dd"], s["hyg_var"].fillna(0)
    mom_neg = s["mom12"] == "12 mesi negativi"
    credito_ok = hyg > -0.03
    strong = (vix > 30) | (dd < -0.20) | (hyg < -0.06)
    sell = mom_neg | ((hyg <= -0.03) & (hyg >= -0.06)) | ((dd < -0.10) & (dd >= -0.20) & (vix >= 20))
    buy = ((dd < -0.05) & (dd >= -0.10) & ~mom_neg & credito_ok) | ((s["epu_pct"] >= 0.9) & credito_ok)
    v = pd.Series("WAIT", index=s.index)
    v[buy] = "BUY"
    v[sell] = "SMALL SELL"
    v[strong] = "STRONG BUY"
    v[s["dd"].isna()] = "WAIT"
    return v


def valuta(s: pd.DataFrame) -> pd.DataFrame:
    s = s.dropna(subset=["fwd_252"])
    dec = decennio(s.index)
    righe = []
    for v in ORDINE:
        g = s[s["verdetto"] == v]
        riga = {"verdetto": v, "giorni": len(g), "quota_tempo_%": 100 * len(g) / len(s)}
        for nome, h in ORIZZONTI.items():
            riga[f"{nome}: media %"] = 100 * g[f"fwd_{h}"].mean()
            riga[f"{nome}: vs sempre investito"] = 100 * (g[f"fwd_{h}"].mean() - s[f"fwd_{h}"].mean())
            riga[f"{nome}: positivi %"] = 100 * (g[f"fwd_{h}"] > 0).mean()
        segni = []
        for d, gd in g.groupby(dec.loc[g.index]):
            if len(gd) >= 60:
                segni.append(np.sign(gd["fwd_126"].mean() - s.loc[dec == d, "fwd_126"].mean()))
        tot = np.sign(riga["6 mesi: vs sempre investito"])
        riga["decenni coerenti"] = f"{sum(1 for x in segni if x == tot)}/{len(segni)}"
        # quanto dura in media un episodio (giorni consecutivi con lo stesso verdetto)
        blocchi = (s["verdetto"] != s["verdetto"].shift()).cumsum()
        durate = s[s["verdetto"] == v].groupby(blocchi).size()
        riga["episodi"] = len(durate)
        riga["durata_media_gg"] = durate.mean()
        righe.append(riga)
    return pd.DataFrame(righe)


def piano_liquidita(s: pd.DataFrame) -> pd.DataFrame:
    """Simulazione: 1.000 € di liquidità nuova ogni mese per 36 anni. Confronta
    (a) investire subito ogni mese, (b) investire in tranche pesate dal verdetto (WAIT 0.5, BUY 1.5, STRONG BUY 3,
    SMALL SELL 0: la liquidità non investita si accumula e viene usata ai verdetti successivi)."""
    mensile = s.resample("ME").last().dropna(subset=["SP"])
    politiche = {
        "ogni mese tutto subito": {"WAIT": 1.0, "BUY": 1.0, "STRONG BUY": 1.0, "SMALL SELL": 1.0},
        "frena su WAIT (0,5), accelera su BUY (1,5) e STRONG BUY (3), zero su SMALL SELL":
            {"WAIT": 0.5, "BUY": 1.5, "STRONG BUY": 3.0, "SMALL SELL": 0.0},
        "tranche normale su WAIT, zero su SMALL SELL, la cassa accumulata va su BUY (2) e STRONG BUY (tutta)":
            {"WAIT": 1.0, "BUY": 2.0, "STRONG BUY": 99.0, "SMALL SELL": 0.0},
        "tranche normale sempre, STRONG BUY spende anche la cassa (solo accelerazione)":
            {"WAIT": 1.0, "BUY": 1.0, "STRONG BUY": 99.0, "SMALL SELL": 1.0},
    }
    esiti = {}
    for nome, pesi in politiche.items():
        quote, cassa, investito, peggior = 0.0, 0.0, 0.0, 0.0
        massimo = 0.0
        for data, riga in mensile.iterrows():
            cassa += 1000
            investito += 1000
            spesa = min(cassa, pesi[riga["verdetto"]] * 1000)
            quote += spesa / riga["SP"]
            cassa -= spesa
            valore = quote * riga["SP"] + cassa
            massimo = max(massimo, valore)
            peggior = min(peggior, valore / massimo - 1)
        finale = quote * mensile["SP"].iloc[-1] + cassa
        esiti[nome] = {"versato_€": investito, "valore_finale_€": finale, "moltiplicatore": finale / investito,
                       "peggior_calo_%": 100 * peggior, "liquidità_rimasta_€": cassa}
    return pd.DataFrame(esiti).T.rename_axis("politica").reset_index()


def oggi_testo(s: pd.DataFrame) -> str:
    u = s.iloc[-1]
    spiegazioni = {
        "STRONG BUY": "panico o capitolazione: è il momento in cui 36 anni di dati dicono di investire con decisione",
        "BUY": "occasione ordinaria: una tranche più grande del solito",
        "WAIT": "nessuna occasione particolare: tranche ordinaria, niente di più",
        "SMALL SELL": "allarme: ridurre un po', non investire liquidità nuova finché non cambia",
    }
    return (f"## VERDETTO DI OGGI ({s.index[-1]:%d/%m/%Y}): {u['verdetto']}\n\n{spiegazioni[u['verdetto']]}.\n\n"
            + lettura_oggi(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oggi", action="store_true")
    a = ap.parse_args()
    df = pd.read_csv(FILE_REGIME, index_col=0, parse_dates=True) if (a.oggi and FILE_REGIME.exists()) else scarica()
    s = segnali(df)
    s["semaforo"], s["punti"] = semaforo(s)
    s["verdetto"] = verdetti(s)
    if a.oggi:
        print(oggi_testo(s))
        return
    val = valuta(s)
    piano = piano_liquidita(s)
    testo = [oggi_testo(s), "\n## Cosa è successo dopo ogni verdetto (1990-oggi)\n",
             md(val[["verdetto", "quota_tempo_%", "episodi", "durata_media_gg", "3 mesi: vs sempre investito",
                     "6 mesi: vs sempre investito", "12 mesi: vs sempre investito", "6 mesi: positivi %",
                     "12 mesi: positivi %", "decenni coerenti"]]),
             "\n## 1.000 € al mese per 36 anni: subito, oppure in tranche pesate dal verdetto\n", md(piano),
             "\nPesi: WAIT 0,5 · BUY 1,5 · STRONG BUY 3 · SMALL SELL 0 (la liquidità non usata si accumula per i verdetti dopo).\n",
             "\n## Storico dei verdetti (ultimi 60 giorni)\n",
             md(s[["SP", "VIX", "dd", "hyg_var", "verdetto"]].tail(60).assign(
                 dd=lambda t: 100 * t["dd"], hyg_var=lambda t: 100 * t["hyg_var"]).reset_index()
                .rename(columns={"Date": "data", "dd": "dal_massimo_%", "hyg_var": "HYG_60gg_%"}))]
    RISULTATI.mkdir(parents=True, exist_ok=True)
    (RISULTATI / "verdetto.md").write_text("\n".join(testo), encoding="utf-8")
    val.to_csv(RISULTATI / "verdetto_storico.csv", index=False)
    print(oggi_testo(s))
    print()
    print(md(val[["verdetto", "quota_tempo_%", "episodi", "durata_media_gg", "6 mesi: vs sempre investito",
                  "12 mesi: vs sempre investito", "6 mesi: positivi %", "decenni coerenti"]]))
    print()
    print(md(piano))


if __name__ == "__main__":
    main()
