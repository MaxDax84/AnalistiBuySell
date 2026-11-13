"""Indicatore di regime: quando conviene essere investiti e quando no? (S&P 500, dal 1990)

Uso: python studio/regime.py            (scarica, valuta, scrive risultati/regime.md e stampa la lettura di oggi)
     python studio/regime.py --oggi     (solo la lettura di oggi dai dati già scaricati)

Non prevede le notizie. Misura il REGIME: tendenza dei prezzi, paura (VIX), stress del credito (spread HY),
lavoro (sussidi), curva dei tassi, incertezza di politica economica (EPU, dai giornali), rischio geopolitico (GPR).
Per ogni condizione misura cosa ha fatto l'S&P 500 nei 1-3-6-12 mesi successivi, in 35 anni, e se il
risultato tiene decennio per decennio. Poi combina le condizioni in un semaforo.
"""

import argparse
import io
from datetime import date

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from config import DATI, RISULTATI

FILE_REGIME = DATI / "regime.csv"
ORIZZONTI = {"1 mese": 21, "3 mesi": 63, "6 mesi": 126, "12 mesi": 252}
UA = {"User-Agent": "Mozilla/5.0"}


# ─── scaricamento ────────────────────────────────────────────────────────────

def fred(serie: str) -> pd.Series:
    r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                     params={"id": serie, "cosd": "1985-01-01"}, timeout=30)
    t = pd.read_csv(io.StringIO(r.text), na_values=".")
    return pd.Series(t.iloc[:, 1].values, index=pd.to_datetime(t.iloc[:, 0]), name=serie).dropna()


def epu() -> pd.Series:
    r = requests.get("https://www.policyuncertainty.com/media/All_Daily_Policy_Data.csv", headers=UA, timeout=30)
    t = pd.read_csv(io.StringIO(r.text))
    idx = pd.to_datetime(t[["year", "month", "day"]])
    return pd.Series(t["daily_policy_index"].values, index=idx, name="EPU").sort_index()


def gpr() -> pd.Series | None:
    try:
        r = requests.get("https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls", headers=UA, timeout=60)
        t = pd.read_excel(io.BytesIO(r.content))
        col_data = t.columns[0]
        col = next(c for c in t.columns if str(c).upper().startswith("GPRD") and "ACT" not in str(c).upper()
                   and "THREAT" not in str(c).upper())
        idx = pd.to_datetime(t[col_data].astype(str), errors="coerce", format="mixed")
        s = pd.Series(pd.to_numeric(t[col], errors="coerce").values, index=idx, name="GPR").dropna()
        return s[s.index.notna()].sort_index()
    except Exception as err:
        print("GPR non disponibile:", err)
        return None


def scarica() -> pd.DataFrame:
    print("Scarico S&P 500, VIX, FRED, EPU, GPR...")
    px = yf.download(["^GSPC", "^VIX", "HYG", "^VIX3M", "^SKEW", "^VVIX"], start="1990-01-01",
                     auto_adjust=True, progress=False)["Close"]
    px.index = pd.to_datetime(px.index).tz_localize(None).normalize()
    px = px[px["^GSPC"].notna() | px["^VIX"].notna()]
    # HYG (ETF obbligazioni ad alto rendimento, dal 2007): quando scende, gli spread di credito salgono.
    # Lo spread HY di FRED (BAMLH0A0HYM2) è ridistribuito solo per gli ultimi anni, quindi serve solo per la lettura di oggi.
    # Sentiment: VIX3M (paura a 3 mesi, dal 2006), SKEW (prezzo dell'assicurazione contro i crolli, dal 2000),
    # VVIX (volatilità della volatilità, dal 2007). Put/call CBOE e sondaggio AAII non sono scaricabili liberamente.
    df = pd.DataFrame({"SP": px["^GSPC"].ffill(), "VIX": px["^VIX"].ffill(), "HYG": px["HYG"].ffill(),
                       "VIX3M": px["^VIX3M"].ffill(), "SKEW": px["^SKEW"].ffill(), "VVIX": px["^VVIX"].ffill()})
    serie = {"HY": "BAMLH0A0HYM2", "CURVA": "T10Y3M", "CLAIMS": "ICSA"}
    for nome, codice in serie.items():
        df[nome] = fred(codice).reindex(df.index, method="ffill")
    df["EPU"] = epu().reindex(df.index, method="ffill")
    g = gpr()
    if g is not None:
        df["GPR"] = g.reindex(df.index, method="ffill")
    DATI.mkdir(parents=True, exist_ok=True)
    df.to_csv(FILE_REGIME)
    print(f"  {len(df)} giorni dal {df.index.min():%Y-%m-%d} -> {FILE_REGIME}")
    return df


# ─── segnali ─────────────────────────────────────────────────────────────────

def percentile_mobile(s: pd.Series, finestra: int = 1260) -> pd.Series:
    """Posizione del valore di oggi rispetto agli ultimi 5 anni (0 = minimo, 1 = massimo)."""
    return s.rolling(finestra, min_periods=250).rank(pct=True)


def segnali(df: pd.DataFrame) -> pd.DataFrame:
    s = df.copy()
    s["mm200"] = s["SP"].rolling(200, min_periods=150).mean()
    s["trend"] = np.where(s["SP"] > s["mm200"], "sopra MM200", "sotto MM200")
    s["mom12"] = np.where(s["SP"] / s["SP"].shift(252) - 1 > 0, "12 mesi positivi", "12 mesi negativi")
    s["vix_fascia"] = pd.cut(s["VIX"], [0, 20, 30, np.inf], labels=["VIX < 20", "VIX 20-30", "VIX > 30"]).astype(str)
    s["hy_delta"] = s["HY"] - s["HY"].shift(60)                       # solo per la lettura di oggi
    s["hyg_var"] = s["HYG"] / s["HYG"].shift(60) - 1                   # dal 2007: -3% in 60 gg ≈ spread +1 punto
    s["credito"] = pd.cut(s["hyg_var"], [-np.inf, -0.06, -0.03, np.inf],
                          labels=["credito in forte stress (HYG < -6% in 60 gg)", "credito in stress (HYG -3/-6%)",
                                  "credito tranquillo"]).astype(str)
    s["curva_stato"] = np.where(s["CURVA"] < 0, "curva invertita", "curva normale")
    claims4 = s["CLAIMS"].rolling(20).mean()
    s["claims_var"] = claims4 / claims4.rolling(252).min() - 1
    s["lavoro"] = pd.cut(s["claims_var"], [-np.inf, 0.10, 0.25, np.inf],
                         labels=["sussidi vicini ai minimi", "sussidi +10-25%", "sussidi > +25%"]).astype(str)
    s["epu_pct"] = percentile_mobile(s["EPU"].rolling(30).mean())
    s["incertezza"] = pd.cut(s["epu_pct"], [-0.01, 0.5, 0.9, 1.01],
                             labels=["EPU basso", "EPU alto", "EPU estremo (top 10%)"]).astype(str)
    if "GPR" in s:
        s["gpr_pct"] = percentile_mobile(s["GPR"].rolling(30).mean())
        s["geopolitica"] = pd.cut(s["gpr_pct"], [-0.01, 0.5, 0.9, 1.01],
                                  labels=["GPR basso", "GPR alto", "GPR estremo (top 10%)"]).astype(str)
    # sentiment dalle opzioni
    s["termine"] = s["VIX"] / s["VIX3M"]
    s["struttura_vix"] = pd.cut(s["termine"], [0, 0.9, 1.0, 1.1, np.inf],
                                labels=["calma (VIX < 90% del VIX3M)", "normale (VIX sotto il VIX3M)",
                                        "inversione (VIX sopra il VIX3M)", "forte inversione (VIX > 110%)"]).astype(str)
    s["skew_pct"] = percentile_mobile(s["SKEW"].rolling(20).mean())
    s["skew_fascia"] = pd.cut(s["skew_pct"], [-0.01, 0.2, 0.8, 1.01],
                              labels=["SKEW basso (poca protezione comprata)", "SKEW medio", "SKEW alto (top 20%)"]).astype(str)
    s["vvix_fascia"] = pd.cut(s["VVIX"], [0, 90, 110, np.inf],
                              labels=["VVIX < 90", "VVIX 90-110", "VVIX > 110"]).astype(str)
    s["dd"] = s["SP"] / s["SP"].rolling(252, min_periods=200).max() - 1
    s["ribasso"] = pd.cut(s["dd"], [-np.inf, -0.20, -0.10, -0.05, 0.01],
                          labels=["> 20% sotto il massimo", "10-20% sotto", "5-10% sotto", "vicino al massimo"]).astype(str)
    for nome, h in ORIZZONTI.items():
        s[f"fwd_{h}"] = s["SP"].shift(-h) / s["SP"] - 1
    return s


SEGNALI = {"trend": "Tendenza (prezzo vs media 200 giorni)", "mom12": "Momentum 12 mesi", "vix_fascia": "Paura (VIX)",
           "credito": "Credito (HYG, variazione 60 gg, dal 2007)", "curva_stato": "Curva dei tassi (10 anni - 3 mesi)",
           "lavoro": "Lavoro (sussidi settimanali vs minimo 1 anno)", "incertezza": "Incertezza politica (EPU, 30 gg)",
           "geopolitica": "Rischio geopolitico (GPR, 30 gg)", "ribasso": "Distanza dal massimo di 1 anno",
           "struttura_vix": "Sentiment: struttura a termine del VIX (dal 2006)",
           "skew_fascia": "Sentiment: SKEW, costo della protezione (dal 2000)",
           "vvix_fascia": "Sentiment: VVIX, volatilità della volatilità (dal 2007)",
           "semaforo": "SEMAFORO (condizioni favorevoli)"}


def semaforo(s: pd.DataFrame) -> pd.Series:
    """Conta le condizioni favorevoli. Verde 5-6, giallo 3-4, rosso 0-2."""
    cond = pd.DataFrame({
        "trend": s["trend"] == "sopra MM200",
        "mom12": s["mom12"] == "12 mesi positivi",
        "vix": s["VIX"] < 30,
        "credito": s["hyg_var"].fillna(0) > -0.03,      # prima del 2007 (nessun dato) conta come favorevole
        "lavoro": s["claims_var"].fillna(0) < 0.10,
        "epu": s["epu_pct"].fillna(0.5) < 0.9,
    })
    punti = cond.sum(axis=1)
    return pd.cut(punti, [-1, 2, 4, 6], labels=["ROSSO (0-2)", "GIALLO (3-4)", "VERDE (5-6)"]).astype(str), punti


# ─── valutazione ─────────────────────────────────────────────────────────────

def decennio(idx: pd.DatetimeIndex) -> pd.Series:
    return pd.Series((idx.year // 10 * 10).astype(str) + "s", index=idx)


def valuta(s: pd.DataFrame) -> pd.DataFrame:
    s = s.dropna(subset=["fwd_252"])
    base = {h: s[f"fwd_{h}"].mean() for h in ORIZZONTI.values()}
    dec = decennio(s.index)
    righe = []
    for col, titolo in SEGNALI.items():
        if col not in s:
            continue
        for stato, g in s.groupby(col):
            if stato == "nan" or len(g) < 120:
                continue
            riga = {"indicatore": titolo, "stato": stato, "giorni": len(g), "quota_tempo_%": 100 * len(g) / len(s)}
            for nome, h in ORIZZONTI.items():
                riga[f"{nome}: media %"] = 100 * g[f"fwd_{h}"].mean()
                riga[f"{nome}: vs sempre investito"] = 100 * (g[f"fwd_{h}"].mean() - base[h])
                riga[f"{nome}: positivi %"] = 100 * (g[f"fwd_{h}"] > 0).mean()
            # coerenza: in quanti decenni (con almeno 100 giorni) il segno a 6 mesi è lo stesso del totale?
            segni = []
            for d, gd in g.groupby(dec.loc[g.index]):
                if len(gd) >= 100:
                    segni.append(np.sign(gd["fwd_126"].mean() - s.loc[dec == d, "fwd_126"].mean()))
            tot = np.sign(riga["6 mesi: vs sempre investito"])
            riga["decenni coerenti"] = f"{sum(1 for x in segni if x == tot)}/{len(segni)}"
            righe.append(riga)
    return pd.DataFrame(righe)


def strategie(s: pd.DataFrame) -> pd.DataFrame:
    """Investito nell'S&P 500 solo quando la regola è vera, altrimenti liquidità allo 0% (prudente: i T-bill
    avrebbero reso di più). Rendimento giornaliero applicato con un giorno di ritardo (si decide alla chiusura)."""
    r = s["SP"].pct_change()
    regole = {
        "sempre investito": pd.Series(True, index=s.index),
        "solo sopra la MM200": s["trend"] == "sopra MM200",
        "solo con 12 mesi positivi": s["mom12"] == "12 mesi positivi",
        "solo con VIX < 30": s["VIX"] < 30,
        "solo senza forte stress del credito": s["hyg_var"].fillna(0) > -0.06,
        "solo semaforo VERDE o GIALLO": s["semaforo"] != "ROSSO (0-2)",
        "solo semaforo VERDE": s["semaforo"] == "VERDE (5-6)",
        "sopra MM200 oppure > 20% sotto il massimo": (s["trend"] == "sopra MM200") | (s["dd"] < -0.20),
    }
    righe = []
    inizio = s.index[s["mom12"].notna() & s["SP"].shift(252).notna()][0]   # dal 1991: serve un anno di storia
    r = r[inizio:]
    anni = (r.index[-1] - r.index[0]).days / 365.25
    for nome, regola in regole.items():
        pos = regola.shift(1).fillna(False).astype(bool)[inizio:]
        eq = (1 + r.where(pos, 0.0)).cumprod()
        dd = (eq / eq.cummax() - 1).min()
        annuali = eq.resample("YE").last().pct_change().dropna()
        bh = (1 + r).cumprod().resample("YE").last().pct_change().dropna()
        righe.append({
            "regola": nome, "investito_%": 100 * pos.mean(),
            "rendimento_annuo_%": 100 * (eq.iloc[-1] ** (1 / anni) - 1),
            "peggior_calo_%": 100 * dd, "peggior_anno_%": 100 * annuali.min(),
            "anni_meglio_del_sempre_investito": f"{int((annuali > bh.reindex(annuali.index)).sum())}/{len(annuali)}",
            "10.000€_nel_" + f"{inizio.year}": 10_000 * eq.iloc[-1],
        })
    return pd.DataFrame(righe)


# ─── rapporto ────────────────────────────────────────────────────────────────

def md(tab: pd.DataFrame) -> str:
    t = tab.copy()
    for c in t.columns:
        if t[c].dtype.kind == "f":
            t[c] = t[c].map(lambda v: f"{v:,.1f}".replace(",", ".") if pd.notna(v) else "")
    cols = list(t.columns)
    righe = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    righe += ["| " + " | ".join(str(v) for v in r) + " |" for r in t.values.tolist()]
    return "\n".join(righe)


def lettura_oggi(s: pd.DataFrame) -> str:
    u = s.iloc[-1]
    righe = [f"Lettura al {s.index[-1]:%d/%m/%Y}: S&P 500 {u['SP']:,.0f} ({100 * u['dd']:+.1f}% dal massimo di 1 anno, "
             f"MM200 {u['mm200']:,.0f}), VIX {u['VIX']:.1f}, spread HY {u['HY']:.2f} ({u['hy_delta']:+.2f} in 60 gg), "
             f"HYG {100 * u['hyg_var']:+.1f}% in 60 gg, curva 10a-3m {u['CURVA']:+.2f}, sussidi {100 * u['claims_var']:+.0f}% dal minimo, "
             f"EPU al {100 * u['epu_pct']:.0f}° percentile" + (f", GPR al {100 * u['gpr_pct']:.0f}°" if "gpr_pct" in u else "")]
    for col in ["trend", "mom12", "vix_fascia", "struttura_vix", "skew_fascia", "vvix_fascia", "credito", "curva_stato",
                "lavoro", "incertezza", "geopolitica", "ribasso"]:
        if col in u:
            righe.append(f"  - {SEGNALI[col]}: **{u[col]}**")
    righe.append(f"  - **{u['semaforo']}**, {int(u['punti'])} condizioni favorevoli su 6")
    return "\n".join(righe)


def rapporto(s: pd.DataFrame, val: pd.DataFrame, strat: pd.DataFrame) -> str:
    base = {nome: 100 * s[f"fwd_{h}"].mean() for nome, h in ORIZZONTI.items()}
    pos = {nome: 100 * (s[f"fwd_{h}"] > 0).mean() for nome, h in ORIZZONTI.items()}
    out = ["# Indicatore di regime: quando conviene essere investiti\n",
           f"S&P 500 dal {s.index.min():%d/%m/%Y} al {s.index.max():%d/%m/%Y} ({len(s)} giorni di borsa). "
           "Per ogni condizione: rendimento medio dell'indice nei mesi successivi, differenza rispetto allo stare "
           "sempre investito, quota di esiti positivi, e in quanti decenni il segno della differenza a 6 mesi è lo stesso.\n",
           "Riferimento 'sempre investito': " + ", ".join(f"{k} {base[k]:+.1f}% (positivo {pos[k]:.0f}%)" for k in base) + "\n",
           "## Lettura di oggi\n", lettura_oggi(s), "",
           "## Cosa ha reso ogni condizione (1990-oggi)\n"]
    colonne = ["indicatore", "stato", "quota_tempo_%", "3 mesi: vs sempre investito", "6 mesi: vs sempre investito",
               "12 mesi: vs sempre investito", "6 mesi: positivi %", "12 mesi: positivi %", "decenni coerenti"]
    out.append(md(val[colonne]))
    out.append("\n## Regole di entrata/uscita a confronto (liquidità allo 0% quando si è fuori)\n")
    out.append(md(strat))
    out.append("\n## Come leggerlo\n"
               "- Un indicatore 'funziona' se la colonna 'vs sempre investito' ha segno sensato, 'positivi %' si sposta "
               "davvero rispetto al riferimento e 'decenni coerenti' è pieno. Dove i decenni sono discordi, è rumore.\n"
               "- Le regole di uscita servono a ridurre i cali profondi, non ad aumentare il rendimento: guarda "
               "'peggior_calo' e 'peggior_anno' prima di 'rendimento_annuo'.\n"
               "- Tutte le condizioni sono note alla chiusura del giorno (point-in-time); la posizione cambia il giorno dopo.\n"
               "- Dal 1990 ci sono stati 4 mercati orso veri (2000-02, 2008, 2020, 2022): ogni regola è giudicata su pochi "
               "episodi. Le quote 'positivi %' contano giorni sovrapposti, non episodi indipendenti.\n")
    out.append("\n## Tabella completa\n")
    out.append(md(val))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--oggi", action="store_true", help="solo la lettura di oggi dai dati già scaricati")
    a = ap.parse_args()
    df = pd.read_csv(FILE_REGIME, index_col=0, parse_dates=True) if (a.oggi and FILE_REGIME.exists()) else scarica()
    s = segnali(df)
    s["semaforo"], s["punti"] = semaforo(s)
    if a.oggi:
        print(lettura_oggi(s))
        return
    val = valuta(s)
    strat = strategie(s)
    RISULTATI.mkdir(parents=True, exist_ok=True)
    val.to_csv(RISULTATI / "regime_condizioni.csv", index=False)
    strat.to_csv(RISULTATI / "regime_strategie.csv", index=False)
    (RISULTATI / "regime.md").write_text(rapporto(s, val, strat), encoding="utf-8")
    print(lettura_oggi(s))
    print(f"\nScritto {RISULTATI / 'regime.md'}")


if __name__ == "__main__":
    main()
