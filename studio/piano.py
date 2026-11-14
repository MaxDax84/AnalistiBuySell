"""Backtest del piano "2.000 € su K titoli, ruota con la classifica momentum".

Uso: python studio/piano.py             (numero di titoli e frequenza del controllo; serve data/prezzi_ampi.parquet)
     python studio/piano.py --modelli   (le varianti di modelli.py a confronto, 5 titoli, controllo ogni sera)
     python studio/piano.py --rumore    (quanto conta la fortuna: 5 titoli pescati a caso tra i candidati, 20 volte)

Regola testata:
  ingresso   compro i K titoli col punteggio migliore (percentile >= 90), a parti uguali; filtro "puro" o "prudente"
             (volatilità annua <= 50%). Ordine eseguito alla chiusura del giorno dopo il segnale.
  controllo  ogni N giorni di borsa (1 = ogni sera, 5 = settimanale, 21 = mensile): vendo ciò che è sceso sotto il
             40° percentile e con la cassa compro i migliori non ancora in portafoglio. Con "conferma" C si vende
             solo se il titolo è rimasto sotto soglia per C giorni di fila (evita le vendite per un giorno storto).
  costi      2 € fissi a ordine + 0,2% del controvalore (spread/cambio), su acquisti e vendite.
  tasse      26% sulle plusvalenze realizzate, con le minusvalenze che compensano i guadagni successivi;
             alla fine si "vende tutto" e si paga l'imposta anche sul non realizzato (confronto onesto).
Confronti: SPY (S&P 500) e media di tutti i titoli ammessi, stessa finestra, stessi costi/tasse (acquisto unico).

Si parte da molte date diverse (una ogni mese di borsa) e si tiene per 250 giorni di borsa: così il risultato non
dipende dal giorno fortunato di partenza. Più la corsa unica dal primo giorno disponibile a oggi.
Risultati in risultati/piano.md e risultati/piano_varianti.csv.
"""
import numpy as np
import pandas as pd

import sys

from classifica import fattori, punteggi
from config import DATI, RISULTATI
from prezzi_ampi import carica
from modelli import MODELLI, dati, freno_mercato, opzioni, punteggio, scegli
from universo_ampio import FILE_UNIVERSO_AMPIO, simboli_classifica

CAPITALE = 2000.0
FISSO = 2.0
SPREAD = 0.002
TASSA = 0.26
SOGLIA_IN, SOGLIA_OUT = 0.9, 0.4
ORIZZONTE = 250
PASSO_PARTENZE = 21
VOL_PRUDENTE = 0.50


def tassa_vendita(guadagno: float, credito: float) -> tuple[float, float]:
    """Imposta su una vendita e nuovo credito di minusvalenze."""
    if guadagno < 0:
        return 0.0, credito - guadagno
    usato = min(credito, guadagno)
    return TASSA * (guadagno - usato), credito - usato


def corsa(s, fine, K, filtro, passo, P, PC, SC, VOLA, AMM, liquida_alla_fine=True, conferma=1,
          R=None, corr_max=None, freno=None, rng=None):
    """Simula dal giorno s (segnale) fino a `fine` (incluso). Ritorna dict con valore finale netto e statistiche."""
    N = P.shape[1]
    cassa, credito = CAPITALE, 0.0
    pos = {}                 # j -> [quantità, costo_base_totale]
    n_ordini, costi, tasse = 0, 0.0, 0.0

    def candidati(t, esclusi):
        ok = AMM[t] & (PC[t] >= SOGLIA_IN) & ~np.isnan(P[t + 1])
        if filtro == "prudente":
            ok &= VOLA[t] <= VOL_PRUDENTE
        ok[list(esclusi)] = False
        idx = np.flatnonzero(ok)
        return idx[np.argsort(-SC[t, idx])]

    def compra(j, importo, t):
        nonlocal cassa, n_ordini, costi
        costo = FISSO + SPREAD * importo
        netto = importo - costo
        if netto <= 0 or np.isnan(P[t, j]):
            return
        q = netto / P[t, j]
        cassa -= importo
        costi += costo
        n_ordini += 1
        pos[j] = [q, importo]

    def vendi(j, t):
        nonlocal cassa, credito, n_ordini, costi, tasse
        q, base = pos.pop(j)
        p = P[t, j] if not np.isnan(P[t, j]) else base / q       # titolo sparito: valuta al costo
        lordo = q * p
        costo = FISSO + SPREAD * lordo
        guad = lordo - costo - base
        imposta, credito = tassa_vendita(guad, credito)
        cassa += lordo - costo - imposta
        costi += costo
        tasse += imposta
        n_ordini += 1

    def sceglie_e_compra(t_dec, t_exec, posti):
        if posti <= 0 or cassa < 50 or (freno is not None and freno[t_dec]):
            return
        cand = candidati(t_dec, set(pos))
        if rng is not None:      # prova del rumore: tra i candidati si pesca a caso invece che in ordine di punteggio
            cand = rng.permutation(cand)
        cand = scegli(cand, list(pos), posti, R, t_dec, corr_max)
        if len(cand) == 0:
            return
        quota = cassa / len(cand)
        for j in cand:
            compra(j, quota, t_exec)

    sceglie_e_compra(s, s + 1, K)
    picco, calo = CAPITALE, 0.0
    for t in range(s + 1, fine + 1):
        val = cassa + sum(q * (P[t, j] if not np.isnan(P[t, j]) else b / q) for j, (q, b) in pos.items())
        picco = max(picco, val)
        calo = min(calo, val / picco - 1)
        if (t - s) % passo == 0 and t + 1 <= fine:
            # debole = sotto soglia (o fuori classifica: NaN) per `conferma` giorni di fila
            deboli = [j for j in pos if not np.any(PC[max(t - conferma + 1, 0):t + 1, j] >= SOGLIA_OUT)]
            for j in deboli:
                vendi(j, t + 1)
            sceglie_e_compra(t, t + 1, K - len(pos))
    valore = cassa + sum(q * (P[fine, j] if not np.isnan(P[fine, j]) else b / q) for j, (q, b) in pos.items())
    lordo_fine = valore
    if liquida_alla_fine:
        for j in list(pos):
            q, b = pos[j]
            p = P[fine, j] if not np.isnan(P[fine, j]) else b / q
            guad = q * p - (FISSO + SPREAD * q * p) - b
            imposta, credito = tassa_vendita(guad, credito)
            valore -= imposta + FISSO + SPREAD * q * p
            tasse += imposta
            costi += FISSO + SPREAD * q * p
            n_ordini += 1
    return {"finale": valore, "lordo": lordo_fine, "ordini": n_ordini, "costi": costi, "tasse": tasse, "calo": calo}


def benchmark(serie_prezzo, s, fine):
    """Acquisto unico alla chiusura s+1, venduto a fine, con costi e imposta."""
    p0, p1 = serie_prezzo[s + 1], serie_prezzo[fine]
    netto = CAPITALE - FISSO - SPREAD * CAPITALE
    lordo = netto * p1 / p0
    guad = lordo - FISSO - SPREAD * lordo - CAPITALE
    return lordo - FISSO - SPREAD * lordo - max(0.0, TASSA * guad)


def main():
    close, vol = carica("prezzi_ampi"), carica("volumi_ampi")
    info = pd.read_csv(FILE_UNIVERSO_AMPIO)
    tieni = [c for c in close.columns if c in simboli_classifica(info)]
    close, vol = close[tieni].ffill(limit=3), vol[tieni]
    f = fattori(close, vol, info)
    score, _ = punteggi(f)
    pct = score.rank(axis=1, pct=True)
    P, PC, SC = close.values, pct.values, score.fillna(-9).values
    VOLA = (f["volatilita_60"] * np.sqrt(252)).values
    AMM = f["ammesso"].values.astype(bool)
    spy = pd.read_csv(DATI / "prezzi.csv", index_col=0, parse_dates=True)["SPY"].reindex(close.index).ffill().values
    r = close.pct_change(fill_method=None)
    univ_ret = r.where(f["ammesso"]).mean(axis=1).fillna(0).values
    univ_px = np.cumprod(1 + univ_ret)
    T = len(close)
    primo = int(np.argmax(AMM.sum(axis=1) > 200))
    date = close.index
    print(f"{T} giorni, primo segnale valido {date[primo]:%d/%m/%Y}")

    varianti = [("puro", K, 5, 1) for K in (1, 3, 5, 10)] + [("prudente", K, 5, 1) for K in (1, 3, 5, 10)] + \
               [("prudente", 5, 21, 1), ("puro", 5, 21, 1)] + \
               [(f, 5, 1, c) for f in ("prudente", "puro") for c in (1, 5, 10)]     # controllo ogni sera, con conferma
    partenze = list(range(primo, T - ORIZZONTE - 2, PASSO_PARTENZE))
    righe = []
    bench = []
    for s in partenze:
        fine = s + ORIZZONTE
        bench.append({"spy": benchmark(spy, s, fine), "universo": benchmark(univ_px, s, fine)})
    bench = pd.DataFrame(bench)
    anni_partenza = pd.Series([date[s].year for s in partenze])
    per_anno = []
    for filtro, K, passo, conf in varianti:
        print("...", filtro, K, passo, conf, flush=True)
        ris = pd.DataFrame([corsa(s, s + ORIZZONTE, K, filtro, passo, P, PC, SC, VOLA, AMM, conferma=conf) for s in partenze])
        fin = ris["finale"]
        if (filtro, K, passo, conf) in [("puro", 5, 5, 1), ("prudente", 5, 5, 1), ("prudente", 5, 21, 1), ("prudente", 10, 5, 1),
                                        ("prudente", 5, 1, 1), ("prudente", 5, 1, 5)]:
            for a in sorted(anni_partenza.unique()):
                m = (anni_partenza == a).values
                per_anno.append({"filtro": filtro, "titoli": K, "controllo_gg": passo, "conferma_gg": conf,
                                 "anno_partenza": a, "partenze": int(m.sum()),
                                 "finale mediano €": fin[m].median(), "SPY mediano €": bench["spy"][m].median(),
                                 "peggiore €": fin[m].min(), "batte SPY %": 100 * (fin.values[m] > bench["spy"].values[m]).mean()})
        righe.append({
            "filtro": filtro, "titoli": K, "controllo_gg": passo, "conferma_gg": conf, "partenze": len(partenze),
            "finale mediano €": fin.median(), "finale medio €": fin.mean(), "peggiore €": fin.min(), "migliore €": fin.max(),
            "in guadagno %": 100 * (fin > CAPITALE).mean(), "sotto -20% %": 100 * (fin < 0.8 * CAPITALE).mean(),
            "batte SPY %": 100 * (fin.values > bench["spy"].values).mean(),
            "batte universo %": 100 * (fin.values > bench["universo"].values).mean(),
            "ordini medi": ris["ordini"].mean(), "costi medi €": ris["costi"].mean(), "tasse medie €": ris["tasse"].mean(),
            "calo peggiore mediano %": 100 * ris["calo"].median(),
            "finale lordo di tasse e costi mediano €": ris["lordo"].median(),
        })
    tab = pd.DataFrame(righe)
    tab.loc[len(tab)] = {"filtro": "SPY", "titoli": 1, "controllo_gg": 0, "partenze": len(partenze),
                         "finale mediano €": bench["spy"].median(), "finale medio €": bench["spy"].mean(),
                         "peggiore €": bench["spy"].min(), "migliore €": bench["spy"].max(),
                         "in guadagno %": 100 * (bench["spy"] > CAPITALE).mean(), "sotto -20% %": 100 * (bench["spy"] < 0.8 * CAPITALE).mean()}
    tab.loc[len(tab)] = {"filtro": "universo", "titoli": 0, "controllo_gg": 0, "partenze": len(partenze),
                         "finale mediano €": bench["universo"].median(), "finale medio €": bench["universo"].mean(),
                         "peggiore €": bench["universo"].min(), "migliore €": bench["universo"].max(),
                         "in guadagno %": 100 * (bench["universo"] > CAPITALE).mean(), "sotto -20% %": 100 * (bench["universo"] < 0.8 * CAPITALE).mean()}
    # corsa unica
    s0, fine = primo, T - 2
    unica = []
    for filtro, K, passo in [("puro", 5, 5), ("prudente", 5, 5), ("prudente", 5, 21), ("puro", 10, 5)]:
        c = corsa(s0, fine, K, filtro, passo, P, PC, SC, VOLA, AMM)
        unica.append({"filtro": filtro, "titoli": K, "controllo_gg": passo, "finale €": c["finale"], "ordini": c["ordini"],
                      "costi €": c["costi"], "tasse €": c["tasse"], "calo max %": 100 * c["calo"]})
    unica.append({"filtro": "SPY", "titoli": 1, "controllo_gg": 0, "finale €": benchmark(spy, s0, fine)})
    unica.append({"filtro": "universo", "titoli": 0, "controllo_gg": 0, "finale €": benchmark(univ_px, s0, fine)})
    unica = pd.DataFrame(unica)
    RISULTATI.mkdir(parents=True, exist_ok=True)
    tab.to_csv(RISULTATI / "piano_varianti.csv", index=False)
    per_anno = pd.DataFrame(per_anno)
    per_anno.to_csv(RISULTATI / "piano_per_anno.csv", index=False)
    print(per_anno.round(1).to_string())
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(tab.round(1).T.to_string())
    print(f"\nCorsa unica {date[s0]:%d/%m/%Y} -> {date[fine]:%d/%m/%Y}")
    print(unica.round(1).to_string())
    unica.to_csv(RISULTATI / "piano_unica.csv", index=False)


def confronta_modelli():
    """Ogni variante di modelli.py sulle stesse date di partenza: 5 titoli, controllo ogni sera, conferma 5 sere."""
    base = dati("oggi")
    date, T = base["close"].index, len(base["close"])
    primo = int(np.argmax(base["f"]["ammesso"].values.sum(axis=1) > 200))
    partenze = list(range(primo, T - ORIZZONTE - 2, PASSO_PARTENZE))
    spy = pd.read_csv(DATI / "prezzi.csv", index_col=0, parse_dates=True)["SPY"].reindex(date).ffill().values
    bench = np.array([benchmark(spy, s, s + ORIZZONTE) for s in partenze])
    anni = np.array([date[s].year for s in partenze])
    freno = freno_mercato(date)
    print(f"{len(partenze)} partenze dal {date[primo]:%d/%m/%Y}; giorni con freno di mercato: {100 * freno[primo:].mean():.0f}%")
    righe, per_anno = [], []
    for nome, modello in MODELLI.items():
        o = opzioni(modello)
        d = dati(o["universo"])
        score = punteggio(d, o["segnale"])
        P, PC, SC = d["close"].values, score.rank(axis=1, pct=True).values, score.fillna(-9).values
        VOLA, AMM = (d["f"]["volatilita_60"] * np.sqrt(252)).values, d["f"]["ammesso"].values.astype(bool)
        print("...", nome, flush=True)
        ris = pd.DataFrame([corsa(s, s + ORIZZONTE, 5, "prudente" if o["vol_max"] else "puro", 1, P, PC, SC, VOLA, AMM, conferma=5,
                                  R=d["r"].values, corr_max=o["corr_max"], freno=freno if o["freno"] else None) for s in partenze])
        fin = ris["finale"].values
        riga = {"modello": nome, "finale mediano €": np.median(fin), "finale medio €": fin.mean(), "peggiore €": fin.min(),
                "migliore €": fin.max(), "in guadagno %": 100 * (fin > CAPITALE).mean(), "batte SPY %": 100 * (fin > bench).mean(),
                "vantaggio mediano su SPY €": np.median(fin - bench), "ordini medi": ris["ordini"].mean(),
                "tasse medie €": ris["tasse"].mean(), "calo peggiore mediano %": 100 * ris["calo"].median()}
        for a in sorted(set(anni)):
            m = anni == a
            riga[f"{a}: vs SPY €"] = np.median(fin[m] - bench[m])
        righe.append(riga)
    righe.append({"modello": "SPY", "finale mediano €": np.median(bench), "finale medio €": bench.mean(), "peggiore €": bench.min(),
                  "migliore €": bench.max(), "in guadagno %": 100 * (bench > CAPITALE).mean()})
    tab = pd.DataFrame(righe)
    tab.to_csv(RISULTATI / "piano_modelli.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(tab.round(0).T.to_string())


def rumore(prove: int = 20):
    """Stessa regola, ma i 5 titoli sono pescati a caso tra i candidati (10% migliore, prudenti). Se la forbice tra
    le prove è larga quanto le differenze tra i modelli, quelle differenze sono fortuna e non merito."""
    d = dati("data")
    score = punteggio(d, "rango")
    date, T = d["close"].index, len(d["close"])
    primo = int(np.argmax(dati("oggi")["f"]["ammesso"].values.sum(axis=1) > 200))
    partenze = list(range(primo, T - ORIZZONTE - 2, PASSO_PARTENZE))
    spy = pd.read_csv(DATI / "prezzi.csv", index_col=0, parse_dates=True)["SPY"].reindex(date).ffill().values
    bench = np.array([benchmark(spy, s, s + ORIZZONTE) for s in partenze])
    P, PC, SC = d["close"].values, score.rank(axis=1, pct=True).values, score.fillna(-9).values
    VOLA, AMM = (d["f"]["volatilita_60"] * np.sqrt(252)).values, d["f"]["ammesso"].values.astype(bool)
    righe = []
    for seme in range(prove):
        rng = np.random.default_rng(seme)
        fin = np.array([corsa(s, s + ORIZZONTE, 5, "prudente", 1, P, PC, SC, VOLA, AMM, conferma=5, rng=rng)["finale"] for s in partenze])
        righe.append({"prova": seme, "finale mediano €": np.median(fin), "peggiore €": fin.min(), "batte SPY %": 100 * (fin > bench).mean(),
                      "vantaggio mediano su SPY €": np.median(fin - bench)})
        print(righe[-1], flush=True)
    tab = pd.DataFrame(righe)
    tab.to_csv(RISULTATI / "piano_rumore.csv", index=False)
    print(tab.describe().round(0).to_string())


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    rumore() if "--rumore" in sys.argv else confronta_modelli() if "--modelli" in sys.argv else main()
