"""Classifica di tutte le azioni comprabili: quali hanno più probabilità di battere le altre nei prossimi mesi?

Uso: python studio/classifica.py              (backtest 5 anni + classifica di oggi + confronto col portafoglio)
     python studio/classifica.py --oggi       (solo classifica di oggi e portafoglio)

Quattro fattori sono calcolati e misurati uno per uno nel backtest:
  momentum 12-1   rendimento degli ultimi 12 mesi escluso l'ultimo (+: chi ha corso continua)
  inversione 1m   rendimento dell'ultimo mese (-: chi è appena salito molto tende a rifiatare)
  volatilità 60g  oscillazione giornaliera (-: i titoli tranquilli rendono di più a parità di rischio)
  massimo 52 set. distanza dal massimo di un anno (+: vicino al massimo = tendenza sana)
Il PUNTEGGIO usa solo il momentum (vedi PESI): con un universo fatto dei titoli vivi oggi gli altri tre escono
con il segno rovesciato per distorsione di sopravvivenza, e non si possono valutare con dati gratuiti.
Ogni fattore è trasformato in punteggio standard rispetto agli altri titoli dello stesso mercato (USA / Europa)
nello stesso giorno. Esclusi: titoli poco scambiati e titoli con prezzo inchiodato (acquisizioni in corso).

Il backtest mensile divide i titoli in 10 fasce e misura cosa ha reso ciascuna il mese dopo,
con costi dello 0,2% per operazione. Se la fascia 10 non batte la fascia 1 in modo stabile, la classifica non vale.

Portafoglio: se esiste studio/portafoglio.csv (colonne: Ticker, quantita) mostra dove stanno i tuoi titoli
e suggerisce i cambi solo quando il divario è grande (il tuo sotto il 40° percentile, il candidato sopra il 95°).
"""

import argparse

import numpy as np
import pandas as pd

from config import CARTELLA, RISULTATI
from prezzi_ampi import carica
from universo_ampio import FILE_UNIVERSO_AMPIO, simboli_classifica

FILE_PORTAFOGLIO = CARTELLA / "portafoglio.csv"
CONTROVALORE_MINIMO = 2e6      # $ al giorno (mediana 20 gg): sotto, il titolo non si compra senza muovere il prezzo
COSTO = 0.002                  # 0,2% per operazione
VOL_MINIMA_ANNUA = 0.08        # sotto, il prezzo è inchiodato: società in corso di acquisizione, rendimento futuro ~0
# Fattori calcolati e misurati uno per uno nel backtest. Il PUNTEGGIO usa solo quelli in PESI:
# con un universo fatto dei sopravvissuti di oggi, bassa volatilità e vicinanza al massimo escono col segno
# rovesciato (i volatili falliti mancano, quelli vivi sono saliti): non si possono valutare con dati gratuiti.
FATTORI = {"mom_12_1": +1, "inversione_1m": -1, "volatilita_60": -1, "dist_max_52": +1}
PESI = {"mom_12_1": +1}


# ─── fattori ─────────────────────────────────────────────────────────────────

def fattori(close: pd.DataFrame, vol: pd.DataFrame, info: pd.DataFrame) -> dict[str, pd.DataFrame]:
    r = close.pct_change(fill_method=None)
    f = {
        "mom_12_1": close.shift(21) / close.shift(252) - 1,
        "inversione_1m": close / close.shift(21) - 1,
        "volatilita_60": r.rolling(60, min_periods=40).std(),
        "dist_max_52": close / close.rolling(252, min_periods=200).max() - 1,
    }
    # Londra quota in pence: il controvalore va diviso per 100
    pence = pd.Series([1.0 if not c.endswith(".L") else 0.01 for c in close.columns], index=close.columns)
    controvalore = (close * vol * pence).rolling(20, min_periods=10).median()
    # titoli non presenti in info (fuori dall'universo di oggi): senza suffisso di borsa sono americani
    usa = pd.Series(info.set_index("Symbol")["mercato"].reindex(close.columns).fillna("USA").eq("USA").values, index=close.columns)
    prezzo_ok = ~(usa & (close <= 5))              # il filtro "prezzo > 5" vale solo per gli USA
    viva = f["volatilita_60"] * np.sqrt(252) > VOL_MINIMA_ANNUA
    f["controvalore"] = controvalore
    f["ammesso"] = (controvalore > CONTROVALORE_MINIMO) & prezzo_ok & viva & close.shift(252).notna()
    f["mercato"] = pd.Series(info.set_index("Symbol")["mercato"].reindex(close.columns).fillna("USA").values, index=close.columns)
    f["mercato"] = f["mercato"].where(f["mercato"] == "USA", "Europa")
    return f


def z_giornaliero(tab: pd.DataFrame, ammesso: pd.DataFrame, mercato: pd.Series | None = None) -> pd.DataFrame:
    """Punteggio standard rispetto agli altri titoli dello stesso giorno, dentro lo stesso mercato (USA / Europa)."""
    t = tab.where(ammesso)
    if mercato is None:
        z = t.sub(t.mean(axis=1), axis=0).div(t.std(axis=1), axis=0)
    else:
        pezzi = []
        for m in mercato.unique():
            cols = mercato.index[mercato == m]
            g = t[cols]
            pezzi.append(g.sub(g.mean(axis=1), axis=0).div(g.std(axis=1), axis=0))
        z = pd.concat(pezzi, axis=1)[t.columns]
    return z.clip(-3, 3)


def punteggi(f: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    zs = {nome: segno * z_giornaliero(f[nome], f["ammesso"], f["mercato"]) for nome, segno in FATTORI.items()}
    score = sum(zs[n] * p for n, p in PESI.items()) / sum(abs(p) for p in PESI.values())
    return score.where(f["ammesso"]), zs


# ─── backtest ────────────────────────────────────────────────────────────────

def backtest(score: pd.DataFrame, close: pd.DataFrame, nome: str = "punteggio") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ogni fine mese: 10 fasce per punteggio, rendimento equipesato del mese dopo. Ritorna (per fascia, per mese)."""
    fine_mese = score.resample("ME").last().index
    fine_mese = [d for d in fine_mese if d in score.index or score.index.asof(d) is not pd.NaT]
    date = pd.DatetimeIndex([score.index.asof(d) for d in fine_mese]).dropna().unique()
    date = [d for d in date if d < score.index[-1]]
    righe, prec_top = [], set()
    for i, d in enumerate(date[:-1]):
        d1 = date[i + 1]
        s = score.loc[d].dropna()
        if len(s) < 200:
            continue
        rend = (close.loc[d1] / close.loc[d] - 1).reindex(s.index)
        fascia = pd.qcut(s.rank(method="first"), 10, labels=range(1, 11))
        riga = {"mese": d1, "universo": rend.mean()}
        for k in range(1, 11):
            riga[f"F{k}"] = rend[fascia == k].mean()
        top = set(s.index[fascia == 10])
        riga["ricambio_top"] = 1 - len(top & prec_top) / max(len(top), 1) if prec_top else np.nan
        prec_top = top
        righe.append(riga)
    mensile = pd.DataFrame(righe).set_index("mese")
    ricambio = mensile["ricambio_top"].mean()
    mensile["F10_netto"] = mensile["F10"] - 2 * COSTO * mensile["ricambio_top"].fillna(1)
    anni = len(mensile) / 12
    per_fascia = []
    for k in list(range(1, 11)):
        serie = mensile[f"F{k}"]
        per_fascia.append({"fascia": f"F{k}" + (" (migliori)" if k == 10 else " (peggiori)" if k == 1 else ""),
                           "rendimento_annuo_%": 100 * ((1 + serie).prod() ** (1 / anni) - 1),
                           "vs_universo_annuo_%": 100 * (((1 + serie).prod() ** (1 / anni)) - ((1 + mensile["universo"]).prod() ** (1 / anni))),
                           "mesi_sopra_universo_%": 100 * (serie > mensile["universo"]).mean()})
    per_fascia = pd.DataFrame(per_fascia)
    spread = mensile["F10"] - mensile["F1"]
    riass = pd.DataFrame([{
        "fattore": nome, "mesi": len(mensile),
        "F10-F1 annuo %": 100 * 12 * spread.mean(),
        "F10-F1 ultimi 12 mesi %": 100 * spread.tail(12).sum(),     # dove la distorsione di sopravvivenza pesa meno
        "mesi in cui F10 > F1 %": 100 * (spread > 0).mean(),
        "t": spread.mean() / (spread.std() / np.sqrt(len(spread))),
        "F10 netto costi annuo %": 100 * ((1 + mensile["F10_netto"]).prod() ** (1 / anni) - 1),
        "universo annuo %": 100 * ((1 + mensile["universo"]).prod() ** (1 / anni) - 1),
        "ricambio mensile top %": 100 * ricambio,
    }])
    return per_fascia, riass, mensile


# ─── classifica di oggi e portafoglio ────────────────────────────────────────

def classifica_oggi(score: pd.DataFrame, zs: dict, f: dict, close: pd.DataFrame, info: pd.DataFrame) -> pd.DataFrame:
    d = score.index[-1]
    s = score.loc[d].dropna().sort_values(ascending=False)
    t = pd.DataFrame({"Ticker": s.index, "punteggio": s.values})
    t["percentile"] = 100 * (1 - np.arange(len(t)) / len(t))
    t["prezzo"] = close.loc[d, t["Ticker"]].values
    t["rend_12m_%"] = 100 * f["mom_12_1"].loc[d, t["Ticker"]].values
    t["rend_1m_%"] = 100 * f["inversione_1m"].loc[d, t["Ticker"]].values
    t["volatilita_annua_%"] = 100 * f["volatilita_60"].loc[d, t["Ticker"]].values * np.sqrt(252)
    t["dal_max_52_%"] = 100 * f["dist_max_52"].loc[d, t["Ticker"]].values
    t = t.merge(info[["Symbol", "Nome", "market_cap", "mercato"] + [c for c in ("sector",) if c in info]],
                left_on="Ticker", right_on="Symbol", how="left").drop(columns="Symbol")
    t["market_cap_M$"] = t["market_cap"] / 1e6     # per l'Europa non disponibile dallo screener
    t["data"] = d
    return t.drop(columns="market_cap")


def confronto_portafoglio(oggi: pd.DataFrame) -> str:
    if not FILE_PORTAFOGLIO.exists():
        return ("Nessun portafoglio: crea `studio/portafoglio.csv` con le colonne `Ticker,quantita` "
                "per vedere dove stanno i tuoi titoli e i cambi suggeriti.")
    pf = pd.read_csv(FILE_PORTAFOGLIO)
    pf["Ticker"] = pf["Ticker"].str.upper().str.strip()
    mio = pf.merge(oggi, on="Ticker", how="left")
    righe = ["| titolo | percentile | rend 12m % | dal max 52 % | giudizio |", "|---|---|---|---|---|"]
    for _, r in mio.sort_values("percentile", ascending=False).iterrows():
        if pd.isna(r["percentile"]):
            righe.append(f"| {r['Ticker']} | n/d | | | non in classifica (fuori universo o poca storia) |")
            continue
        g = "bene" if r["percentile"] >= 60 else "nella media" if r["percentile"] >= 40 else "candidato alla sostituzione"
        righe.append(f"| {r['Ticker']} | {r['percentile']:.0f} | {r['rend_12m_%']:+.0f} | {r['dal_max_52_%']:+.0f} | {g} |")
    deboli = mio[mio["percentile"] < 40]["Ticker"].tolist()
    candidati = oggi[(oggi["percentile"] >= 95) & ~oggi["Ticker"].isin(pf["Ticker"])].head(10)
    testo = "\n".join(righe)
    if deboli and len(candidati):
        testo += (f"\n\nTitoli sotto il 40° percentile: {', '.join(deboli)}. Candidati dal 5% migliore non ancora in portafoglio: "
                  + ", ".join(f"{r['Ticker']} ({r['percentile']:.0f}°)" for _, r in candidati.iterrows())
                  + ". Un cambio ha senso solo se il divario resta per qualche settimana: la classifica cambia ogni giorno, le tasse no.")
    return testo


def md(tab: pd.DataFrame) -> str:
    t = tab.copy()
    for c in t.columns:
        if t[c].dtype.kind == "f":
            t[c] = t[c].map(lambda v: f"{v:,.1f}".replace(",", ".") if pd.notna(v) else "")
    cols = list(t.columns)
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
                     + ["| " + " | ".join(str(v) for v in r) + " |" for r in t.values.tolist()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oggi", action="store_true")
    a = ap.parse_args()
    close, vol = carica("prezzi_ampi"), carica("volumi_ampi")
    info = pd.read_csv(FILE_UNIVERSO_AMPIO)
    # solo i titoli dell'universo attuale (USA > 1 mld $ + Europa)
    tieni = [c for c in close.columns if c in simboli_classifica(info)]
    close, vol = close[tieni], vol[tieni]
    # calendari diversi (USA ed Europa): nei giorni di festa di una borsa si porta avanti l'ultimo prezzo
    close = close.ffill(limit=3)
    f = fattori(close, vol, info)
    score, zs = punteggi(f)
    oggi = classifica_oggi(score, zs, f, close, info[info["Symbol"].isin(tieni)])
    RISULTATI.mkdir(parents=True, exist_ok=True)
    oggi.to_csv(RISULTATI / "classifica_oggi.csv", index=False)
    d = score.index[-1]
    testo = [f"# Classifica di tutte le azioni comprabili ({len(oggi)} titoli, al {d:%d/%m/%Y})\n",
             "## I primi 25\n", md(oggi.head(25)[["Ticker", "Nome", "mercato", "percentile", "prezzo", "rend_12m_%", "rend_1m_%",
                                                  "volatilita_annua_%", "dal_max_52_%", "market_cap_M$"]]),
             "\n## I primi 15 europei\n", md(oggi[oggi["mercato"] != "USA"].head(15)[["Ticker", "Nome", "mercato", "percentile", "prezzo",
                                                                                        "rend_12m_%", "rend_1m_%", "volatilita_annua_%", "dal_max_52_%"]]),
             "\n## Il tuo portafoglio\n", confronto_portafoglio(oggi)]
    if not a.oggi:
        print("Backtest del punteggio combinato...")
        per_fascia, riass, mensile = backtest(score, close)
        riassunti = [riass]
        for nome, segno in FATTORI.items():
            print(f"  fattore {nome}...")
            _, r1, _ = backtest(segno * z_giornaliero(f[nome], f["ammesso"], f["mercato"]).where(f["ammesso"]), close, nome)
            riassunti.append(r1)
        riassunti = pd.concat(riassunti, ignore_index=True)
        per_anno = mensile.groupby(mensile.index.year).apply(
            lambda g: pd.Series({"F10 %": 100 * ((1 + g["F10"]).prod() - 1), "F1 %": 100 * ((1 + g["F1"]).prod() - 1),
                                 "universo %": 100 * ((1 + g["universo"]).prod() - 1), "mesi": len(g)}))
        testo += ["\n## Il backtest: le 10 fasce, mese dopo mese, 5 anni\n", md(per_fascia),
                  "\n## Ogni fattore da solo, e combinati\n", md(riassunti),
                  "\n## Anno per anno (fascia migliore, peggiore, universo)\n", md(per_anno.reset_index().rename(columns={"mese": "anno"})),
                  "\n## Avvertenze\n- L'universo è quello quotato OGGI: chi è fallito o è stato ritirato dal listino non c'è. "
                  "I rendimenti assoluti sono gonfiati; le differenze tra fasce lo sono meno, ma non sono immuni.\n"
                  "- 5 anni = 60 mesi: pochi. Un fattore che funziona da 60 anni in letteratura può avere 5 anni cattivi.\n"
                  "- Costi 0,2% per operazione; niente tasse. Con ricambio mensile alto, le tasse sui guadagni pesano.\n"]
        per_fascia.to_csv(RISULTATI / "classifica_fasce.csv", index=False)
        riassunti.to_csv(RISULTATI / "classifica_fattori.csv", index=False)
        mensile.to_csv(RISULTATI / "classifica_mensile.csv")
    (RISULTATI / "classifica.md").write_text("\n".join(testo), encoding="utf-8")
    print(f"Scritto {RISULTATI / 'classifica.md'}")
    print(md(oggi.head(10)[["Ticker", "percentile", "rend_12m_%", "rend_1m_%", "volatilita_annua_%", "dal_max_52_%", "market_cap_M$"]]))


if __name__ == "__main__":
    main()
