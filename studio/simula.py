"""Simulatore in euro: quanto avrei fatto investendo 10.000 € in un titolo in un dato giorno / in un dato stato?

Esempi:
  python simula.py AAPL --da 2024-03-01 --giorni 60
      10.000 € su AAPL alla chiusura del 1/3/2024, venduti 60 giorni di borsa dopo; stato degli analisti quel giorno.

  python simula.py AAPL --confronta etichetta --giorni 60
      media di 10.000 € investiti su AAPL in TUTTI i giorni in cui il consenso era Compra, contro Tieni, contro Vendi.
      --confronta accetta: etichetta, upside, tendenza, upgrade. Senza ticker: tutti i 300 titoli.

  python simula.py --strategie --giorni 20 60 250
      confronto in euro di tutte le regole d'ingresso (consenso, upside, tendenza...) su tutti i titoli.

Ogni risultato riporta anche "vs media titoli": quanto quella scelta ha reso in più (o in meno) rispetto
a investire la stessa cifra, lo stesso giorno, nella media dei 300 titoli. È il confronto onesto:
dice se l'indicatore sceglie il titolo giusto, non se il mercato saliva.
"""

import argparse
import sys

import numpy as np
import pandas as pd
from scipy import stats

from config import BENCHMARK
from indicatori import stato_giornaliero

IMPORTO = 10_000


# ─── rendimenti ──────────────────────────────────────────────────────────────

def tabelle_rendimenti(prezzi: pd.DataFrame, giorni: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """(rendimento titoli, rendimento in eccesso sulla media, rendimento SPY) da chiusura a chiusura + giorni."""
    titoli = prezzi.drop(columns=[BENCHMARK])
    r = titoli.shift(-giorni) / titoli - 1
    spy = prezzi[BENCHMARK].shift(-giorni) / prezzi[BENCHMARK] - 1
    return r, r.sub(r.mean(axis=1), axis=0), spy


def rendimenti_di(entrate: pd.DataFrame, r: pd.DataFrame, ecc: pd.DataFrame) -> pd.DataFrame:
    """Per ogni riga (Ticker, Data) di 'entrate' aggiunge il rendimento assoluto e in eccesso."""
    ir = r.index.get_indexer(entrate["Data"])
    ic = r.columns.get_indexer(entrate["Ticker"])
    ok = (ir >= 0) & (ic >= 0)
    out = entrate[ok].copy()
    out["rend"] = r.values[ir[ok], ic[ok]]
    out["ecc"] = ecc.values[ir[ok], ic[ok]]
    return out.dropna(subset=["rend"])


def riga_euro(nome: str, res: pd.DataFrame) -> dict:
    """Riassunto in euro di un insieme di investimenti da 10.000 € l'uno.

    'vs media per titolo' pesa ogni titolo allo stesso modo (prima la media dentro il titolo, poi tra titoli):
    se una regola sembra buona solo perché seleziona spesso 2-3 titoli esplosi, qui si vede.
    'stesso segno nelle 2 metà' = il vantaggio ha lo stesso segno nella prima e nella seconda metà del periodo.
    """
    if len(res) == 0:
        return {"regola": nome, "n_ingressi": 0}
    t = stats.ttest_1samp(res["ecc"], 0).statistic if len(res) > 2 else np.nan
    per_titolo = res.groupby("Ticker")["ecc"].mean()
    meta = res["Data"].median()
    prima, dopo = res[res["Data"] < meta]["ecc"].mean(), res[res["Data"] >= meta]["ecc"].mean()
    return {
        "regola": nome,
        "n_ingressi": len(res),
        "n_titoli": res["Ticker"].nunique(),
        "valore_finale_medio_€": IMPORTO * (1 + res["rend"].mean()),
        "valore_finale_mediano_€": IMPORTO * (1 + res["rend"].median()),
        "in_guadagno_%": 100 * (res["rend"] > 0).mean(),
        "vs_media_titoli_€": IMPORTO * res["ecc"].mean(),
        "vs_media_per_titolo_€": IMPORTO * per_titolo.mean(),
        "batte_la_media_%": 100 * (res["ecc"] > 0).mean(),
        "stesso_segno_2_metà": "sì" if np.sign(prima) == np.sign(dopo) and prima != 0 else "no",
        "t": t,
    }


def stampa(tab: pd.DataFrame) -> None:
    t = tab.copy()
    for c in t.columns:
        if c.endswith("€"):
            t[c] = t[c].map(lambda v: f"{v:,.0f}".replace(",", ".") if pd.notna(v) else "")
        elif c.endswith("%") or c == "t":
            t[c] = t[c].map(lambda v: f"{v:.1f}" if pd.notna(v) else "")
    print(t.to_string(index=False))


# ─── regole d'ingresso ───────────────────────────────────────────────────────

def regole(stato: pd.DataFrame) -> dict[str, pd.DataFrame]:
    s = stato[stato["n_banche"] >= 5].copy()
    s["diventa_compra"] = (s["etichetta"] == "Compra") & (s.groupby("Ticker")["etichetta"].shift() != "Compra")
    s["ups_q"] = s.groupby("Data")["upside_%"].rank(pct=True)
    return {
        "giorno qualsiasi (riferimento)": s,
        "consenso = Compra": s[s["etichetta"] == "Compra"],
        "consenso = Tieni": s[s["etichetta"] == "Tieni"],
        "consenso = Vendi": s[s["etichetta"] == "Vendi"],
        "il giorno in cui diventa Compra": s[s["diventa_compra"]],
        "almeno 1 upgrade negli ultimi 20 gg": s[s["alza_20"] >= 1],
        "almeno 2 upgrade negli ultimi 20 gg": s[s["alza_20"] >= 2],
        "almeno 2 downgrade negli ultimi 20 gg": s[s["abbassa_20"] >= 2],
        "upside <= 5%": s[s["upside_%"] <= 5],
        "upside 5-15%": s[(s["upside_%"] > 5) & (s["upside_%"] <= 15)],
        "upside 15-30%": s[(s["upside_%"] > 15) & (s["upside_%"] <= 30)],
        "upside > 30%": s[s["upside_%"] > 30],
        "upside nel 20% più alto del giorno": s[s["ups_q"] >= 0.8],
        "upside nel 20% più basso del giorno": s[s["ups_q"] <= 0.2],
        "consenso in salita (+0.25 in 20 gg)": s[s["tendenza_20"] >= 0.25],
        "consenso in discesa (-0.25 in 20 gg)": s[s["tendenza_20"] <= -0.25],
        "target alzato > 5% in 20 gg": s[s["target_var_20_%"] > 5],
        "target abbassato > 5% in 20 gg": s[s["target_var_20_%"] < -5],
        "Compra + upside > 20% + consenso in salita": s[(s["etichetta"] == "Compra") & (s["upside_%"] > 20) & (s["tendenza_20"] > 0)],
        "Compra + upside < 5%": s[(s["etichetta"] == "Compra") & (s["upside_%"] < 5)],
    }


def fasce_confronto(s: pd.DataFrame, criterio: str) -> pd.Series:
    if criterio == "etichetta":
        return s["etichetta"]
    if criterio == "upside":
        return pd.cut(s["upside_%"], [-np.inf, 0, 5, 15, 30, np.inf],
                      labels=["upside < 0", "0-5%", "5-15%", "15-30%", "> 30%"]).astype(str)
    if criterio == "tendenza":
        return pd.cut(s["tendenza_20"], [-np.inf, -0.25, 0.25, np.inf],
                      labels=["in discesa", "stabile", "in salita"]).astype(str)
    if criterio == "upgrade":
        return pd.cut(s["alza_20"], [-1, 0, 1, np.inf], labels=["nessuno", "1", "2 o più"]).astype(str)
    raise SystemExit(f"criterio sconosciuto: {criterio}")


# ─── comandi ─────────────────────────────────────────────────────────────────

def comando_singolo(stato, prezzi, ticker, da, giorni, importo):
    prezzi_t = prezzi[ticker].dropna()
    pos = prezzi_t.index.searchsorted(pd.Timestamp(da))
    if pos + giorni >= len(prezzi_t):
        raise SystemExit("non ci sono abbastanza giorni dopo quella data")
    d0, d1 = prezzi_t.index[pos], prezzi_t.index[pos + giorni]
    p0, p1 = prezzi_t.iloc[pos], prezzi_t.iloc[pos + giorni]
    spy = prezzi[BENCHMARK]
    r_spy = spy.loc[d1] / spy.loc[d0] - 1
    media = (prezzi.drop(columns=[BENCHMARK]).loc[d1] / prezzi.drop(columns=[BENCHMARK]).loc[d0] - 1).mean()
    riga = stato[(stato["Ticker"] == ticker) & (stato["Data"] == d0)]
    print(f"{importo:,.0f} € su {ticker} alla chiusura del {d0:%d/%m/%Y} ({p0:.2f}), venduti il {d1:%d/%m/%Y} ({p1:.2f}):")
    print(f"  -> {importo * p1 / p0:,.0f} €  ({100 * (p1 / p0 - 1):+.1f}%)")
    print(f"  stessa cifra su {BENCHMARK}: {importo * (1 + r_spy):,.0f} € ({100 * r_spy:+.1f}%) | "
          f"sulla media dei 300 titoli: {importo * (1 + media):,.0f} € ({100 * media:+.1f}%)")
    if len(riga):
        r = riga.iloc[0]
        print(f"  quel giorno gli analisti dicevano: {r['etichetta']} (punteggio {r['score']:.2f} su {int(r['n_banche'])} banche), "
              f"target {r['target']:.0f} = upside {r['upside_%']:+.0f}%, tendenza 20gg {r['tendenza_20']:+.2f}, "
              f"upgrade/downgrade 20gg {int(r['alza_20'])}/{int(r['abbassa_20'])}")
    else:
        print("  (nessun dato degli analisti per quel giorno)")


def comando_confronta(stato, prezzi, ticker, criterio, giorni, importo):
    s = stato if ticker is None else stato[stato["Ticker"] == ticker]
    s = s[s["n_banche"] >= 5].copy()
    s["fascia"] = fasce_confronto(s, criterio)
    r, ecc, _ = tabelle_rendimenti(prezzi, giorni)
    righe = []
    for fascia, g in s.groupby("fascia"):
        righe.append(riga_euro(fascia, rendimenti_di(g, r, ecc)))
    dove = ticker or "tutti i 300 titoli"
    print(f"{importo:,.0f} € investiti su {dove} in ogni giorno con quello stato, venduti dopo {giorni} giorni di borsa, per '{criterio}':\n")
    stampa(pd.DataFrame(righe))


def comando_strategie(stato, prezzi, lista_giorni):
    tutte = []
    for giorni in lista_giorni:
        r, ecc, _ = tabelle_rendimenti(prezzi, giorni)
        righe = [riga_euro(nome, rendimenti_di(g, r, ecc)) for nome, g in regole(stato).items()]
        print(f"\n=== {IMPORTO:,.0f} € per ogni ingresso, venduti dopo {giorni} giorni di borsa (tutti i titoli, 5+ banche) ===\n")
        tab = pd.DataFrame(righe)
        stampa(tab)
        tab.insert(1, "giorni", giorni)
        tutte.append(tab)
    from indicatori import RISULTATI
    pd.concat(tutte, ignore_index=True).to_csv(RISULTATI / "strategie.csv", index=False)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")   # il simbolo € nella console di Windows
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ticker", nargs="?", help="es. AAPL (vuoto = tutti)")
    ap.add_argument("--da", help="data d'ingresso AAAA-MM-GG")
    ap.add_argument("--confronta", choices=["etichetta", "upside", "tendenza", "upgrade"])
    ap.add_argument("--strategie", action="store_true")
    ap.add_argument("--giorni", type=int, nargs="+", default=[60], help="giorni di borsa di detenzione")
    ap.add_argument("--importo", type=float, default=IMPORTO)
    ap.add_argument("--ricalcola", action="store_true", help="rigenera lo stato giornaliero")
    a = ap.parse_args()

    stato, prezzi = stato_giornaliero(ricalcola=a.ricalcola)
    if a.strategie:
        comando_strategie(stato, prezzi, a.giorni)
    elif a.confronta:
        comando_confronta(stato, prezzi, a.ticker, a.confronta, a.giorni[0], a.importo)
    elif a.ticker and a.da:
        comando_singolo(stato, prezzi, a.ticker.upper(), a.da, a.giorni[0], a.importo)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
