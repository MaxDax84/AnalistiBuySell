"""Quanto è affidabile il consenso degli analisti e per quanto tempo?

Uso: python studio/analisi.py
Legge data/prezzi.csv e data/azioni_analisti.csv, scrive in risultati/:
  riepilogo.md          le risposte in italiano, con le tabelle
  eventi.csv            rendimento in eccesso medio dopo ogni tipo di segnale, per orizzonte
  fasce.csv             rendimento in eccesso per fascia di consenso (ogni giorno, tutti i titoli)
  grafici.html          curve interattive (Plotly)

Tutti i rendimenti sono IN ECCESSO rispetto a SPY: quanto il titolo ha fatto in più (o in meno)
del mercato. Così un mercato che sale non fa sembrare buoni tutti i "Compra".
"""

import numpy as np
import pandas as pd
from scipy import stats

from config import BENCHMARK, FILE_AZIONI, FILE_PREZZI, ORIZZONTI, RISULTATI
from consenso import consenso_giornaliero, eventi, giudizi_non_mappati

# Un segnale ogni N giorni per titolo è già moltissimo: orizzonti lunghi hanno finestre
# sovrapposte, quindi la t di Student va letta come indicativa, non come verità assoluta.


def carica() -> tuple[pd.DataFrame, pd.DataFrame]:
    prezzi = pd.read_csv(FILE_PREZZI, index_col=0, parse_dates=True).sort_index()
    prezzi = prezzi.dropna(axis=1, how="all")
    azioni = pd.read_csv(FILE_AZIONI, parse_dates=["Data"])
    return prezzi, azioni


def rendimenti_in_eccesso(prezzi: pd.DataFrame) -> dict[int, pd.DataFrame]:
    """Per ogni orizzonte h: tabella giorni x titoli con il rendimento del titolo meno la MEDIA dei 300 titoli
    nello stesso periodo (da chiusura a chiusura+h).

    Perché non SPY: l'universo sono i 300 titoli più grandi OGGI, cioè i vincitori degli ultimi anni, che
    battono SPY per costruzione. Confrontando con la media dell'universo resta solo la domanda che conta:
    gli analisti distinguono i titoli migliori dai peggiori? L'orizzonte 0 è la reazione del giorno stesso
    del segnale (dalla chiusura precedente alla chiusura del giorno), che chi agisce a fine giornata non prende.
    """
    titoli = prezzi.drop(columns=[BENCHMARK])
    esito = {}
    for h in [0] + ORIZZONTI:
        r = titoli.shift(-h) / titoli - 1 if h > 0 else titoli / titoli.shift(1) - 1
        esito[h] = r.sub(r.mean(axis=1), axis=0)
    return esito


def studio_eventi(ev: pd.DataFrame, eccesso: dict[int, pd.DataFrame]) -> pd.DataFrame:
    righe = []
    for tipo, gruppo in ev.groupby("tipo"):
        for h, tab in eccesso.items():
            # prendi il rendimento in eccesso del titolo alla data del segnale
            idx_r = tab.index.get_indexer(gruppo["Data_segnale"])
            idx_c = tab.columns.get_indexer(gruppo["Ticker"])
            ok = (idx_r >= 0) & (idx_c >= 0)
            valori = tab.values[idx_r[ok], idx_c[ok]]
            valori = valori[~np.isnan(valori)]
            if len(valori) < 30:
                continue
            t, p = stats.ttest_1samp(valori, 0.0)
            righe.append({
                "segnale": tipo, "orizzonte_gg": h, "n": len(valori),
                "eccesso_medio_%": 100 * valori.mean(),
                "eccesso_mediano_%": 100 * np.median(valori),
                "quota_positivi_%": 100 * (valori > 0).mean(),
                "t": t, "p": p,
            })
    return pd.DataFrame(righe)


def studio_fasce(cons: pd.DataFrame, eccesso: dict[int, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Ogni giorno divide i titoli per etichetta e per quintile di punteggio; media del rendimento in eccesso."""
    cons = cons[cons["n_banche"] >= 5].copy()   # con meno di 5 banche il consenso è rumore
    cons["quintile"] = cons.groupby("Data")["score"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=["Q1 peggiori", "Q2", "Q3", "Q4", "Q5 migliori"]))
    righe_et, righe_q, ic = [], [], {}
    for h, tab in eccesso.items():
        if h == 0:
            continue
        lungo = tab.stack().rename("ecc").reset_index()
        lungo.columns = ["Data", "Ticker", "ecc"]
        unito = cons.merge(lungo, on=["Data", "Ticker"], how="inner")
        for et, g in unito.groupby("etichetta"):
            righe_et.append({"fascia": et, "orizzonte_gg": h, "n": len(g),
                             "eccesso_medio_%": 100 * g["ecc"].mean(),
                             "quota_positivi_%": 100 * (g["ecc"] > 0).mean()})
        for q, g in unito.groupby("quintile", observed=True):
            righe_q.append({"fascia": str(q), "orizzonte_gg": h, "n": len(g),
                            "eccesso_medio_%": 100 * g["ecc"].mean(),
                            "quota_positivi_%": 100 * (g["ecc"] > 0).mean()})
        # correlazione di Spearman giornaliera tra punteggio e rendimento futuro (information coefficient)
        giorn = unito.groupby("Data").apply(
            lambda g: stats.spearmanr(g["score"], g["ecc"])[0] if len(g) >= 30 else np.nan,
            include_groups=False).dropna()
        ic[h] = {"ic_medio": giorn.mean(), "ic_t": giorn.mean() / (giorn.std() / np.sqrt(len(giorn))),
                 "giorni": len(giorn), "quota_giorni_ic_positivo_%": 100 * (giorn > 0).mean()}
    fasce = pd.concat([pd.DataFrame(righe_et), pd.DataFrame(righe_q)], ignore_index=True)
    return fasce, pd.DataFrame(ic).T.rename_axis("orizzonte_gg").reset_index()


def grafici(ev_tab: pd.DataFrame, fasce: pd.DataFrame) -> str:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=2, cols=1, subplot_titles=(
        "Rendimento in eccesso medio dopo il segnale (%)", "Rendimento in eccesso medio per fascia di consenso (%)"))
    for tipo, g in ev_tab[ev_tab["orizzonte_gg"] > 0].groupby("segnale"):
        fig.add_trace(go.Scatter(x=g["orizzonte_gg"], y=g["eccesso_medio_%"], mode="lines+markers", name=tipo), row=1, col=1)
    for fascia, g in fasce.groupby("fascia"):
        fig.add_trace(go.Scatter(x=g["orizzonte_gg"], y=g["eccesso_medio_%"], mode="lines+markers", name=fascia), row=2, col=1)
    fig.update_xaxes(title_text="giorni di borsa dopo il segnale", type="log")
    fig.update_layout(height=900, title="Affidabilità del consenso degli analisti (S&P 500, rendimento oltre SPY)")
    return fig.to_html(include_plotlyjs="cdn")


def tabella_md(tab: pd.DataFrame, colonne: list[str]) -> str:
    t = tab[colonne].copy()
    for c in t.columns:
        if t[c].dtype.kind == "f":
            t[c] = t[c].map(lambda v: f"{v:.2f}")
    righe = ["| " + " | ".join(colonne) + " |", "|" + "|".join("---" for _ in colonne) + "|"]
    righe += ["| " + " | ".join(str(v) for v in r) + " |" for r in t.values.tolist()]
    return "\n".join(righe)


def riepilogo(ev_tab: pd.DataFrame, fasce: pd.DataFrame, ic: pd.DataFrame, cons: pd.DataFrame,
              ev: pd.DataFrame, prezzi: pd.DataFrame) -> str:
    out = ["# Quanto sono affidabili i giudizi degli analisti?\n",
           f"Universo: {prezzi.shape[1] - 1} titoli S&P 500 per capitalizzazione, prezzi dal "
           f"{prezzi.index.min():%d/%m/%Y} al {prezzi.index.max():%d/%m/%Y}. "
           f"Segnali analizzati: {len(ev)}. Rendimenti sempre IN ECCESSO rispetto alla media dei 300 titoli "
           "nello stesso periodo (vedi avvertenze: non SPY), da chiusura del giorno del segnale a chiusura dopo "
           "N giorni di borsa. Niente costi di transazione.\n"]

    out.append("## 1. Se seguo un segnale oggi, quando devo uscire?\n")
    out.append("Per ogni tipo di segnale: l'orizzonte in cui il rendimento medio in eccesso è massimo, "
               "e se quel vantaggio è distinguibile dal caso (|t| > 2 ≈ sì).\n")
    righe = []
    for tipo, g in ev_tab.groupby("segnale"):
        negativo = "abbassa" in tipo or tipo.endswith("Vendi") or tipo.startswith("consenso: Compra")
        dopo = g[g["orizzonte_gg"] > 0]
        migliore = dopo.loc[dopo["eccesso_medio_%"].idxmin() if negativo else dopo["eccesso_medio_%"].idxmax()]
        g0 = g[g["orizzonte_gg"] == 0]
        a1 = g[g["orizzonte_gg"] == 1]
        righe.append({"segnale": tipo, "n_segnali": int(g["n"].max()),
                      "giorno_del_segnale_%": g0["eccesso_medio_%"].iloc[0] if len(g0) else np.nan,
                      "dopo_1gg_%": a1["eccesso_medio_%"].iloc[0] if len(a1) else np.nan,
                      "orizzonte_effetto_max_gg": int(migliore["orizzonte_gg"]),
                      "effetto_max_medio_%": migliore["eccesso_medio_%"],
                      "effetto_max_mediano_%": migliore["eccesso_mediano_%"],
                      "quota_positivi_%": migliore["quota_positivi_%"], "t": migliore["t"]})
    out.append(tabella_md(pd.DataFrame(righe), ["segnale", "n_segnali", "giorno_del_segnale_%", "dopo_1gg_%",
                                                 "orizzonte_effetto_max_gg", "effetto_max_medio_%",
                                                 "effetto_max_mediano_%", "quota_positivi_%", "t"]))
    out.append("\n'giorno_del_segnale' = quanto il titolo si è mosso (oltre la media) nel giorno stesso dell'annuncio: "
               "chi compra alla chiusura NON lo prende. Le colonne dopo misurano cosa resta da prendere. "
               "Per i segnali negativi (abbassa, -> Vendi, Compra -> Tieni) l'effetto 'giusto' è negativo: "
               "il titolo fa peggio della media. Se la media è alta ma la mediana è negativa, pochi titoli "
               "esplosi trascinano la media e il titolo tipico ha perso.\n")

    out.append("## 2. Il consenso del giorno dice qualcosa sul futuro?\n")
    out.append("Ogni giorno i titoli sono divisi in 5 fasce per punteggio del consenso (solo titoli con almeno 5 banche). "
               "Se gli analisti avessero ragione, Q5 dovrebbe battere Q1 in modo crescente con l'orizzonte.\n")
    q = fasce[fasce["fascia"].str.startswith("Q")].pivot(index="orizzonte_gg", columns="fascia", values="eccesso_medio_%")
    q["Q5 - Q1"] = q["Q5 migliori"] - q["Q1 peggiori"]
    out.append(tabella_md(q.reset_index(), ["orizzonte_gg"] + list(q.columns)))
    out.append("\nCorrelazione (Spearman) giornaliera tra punteggio e rendimento futuro, mediata sui giorni: "
               "positiva = gli analisti ordinano bene i titoli; t > 2 ≈ non è caso.\n")
    out.append(tabella_md(ic, ["orizzonte_gg", "ic_medio", "ic_t", "giorni", "quota_giorni_ic_positivo_%"]))

    et = fasce[~fasce["fascia"].str.startswith("Q")].pivot(index="orizzonte_gg", columns="fascia", values="eccesso_medio_%")
    out.append("\nStesso confronto con le etichette fisse (Compra ≥ 4.0, Tieni, Vendi < 3.0):\n")
    out.append(tabella_md(et.reset_index(), ["orizzonte_gg"] + list(et.columns)))
    dist = cons.drop_duplicates(["Ticker", "Data"])["etichetta"].value_counts(normalize=True) * 100
    out.append("\nQuanto sono frequenti le etichette (giorni-titolo): " +
               ", ".join(f"{k} {v:.0f}%" for k, v in dist.items()) + ". Gli analisti dicono quasi sempre Compra o Tieni.\n")

    out.append("## 3. Tabella completa per segnale e orizzonte\n")
    out.append(tabella_md(ev_tab, ["segnale", "orizzonte_gg", "n", "eccesso_medio_%", "eccesso_mediano_%",
                                   "quota_positivi_%", "t", "p"]))
    out.append("\n## Avvertenze\n- Le finestre di orizzonti lunghi si sovrappongono: le t sono ottimistiche, "
               "contano soprattutto il segno e l'ordine di grandezza.\n- Nessun costo di transazione né tasse.\n"
               "- L'universo sono i 300 titoli più grandi OGGI: i vincitori degli ultimi anni. Rispetto a SPY "
               "battono tutti, anche quelli con 'Vendi', per costruzione. Per questo l'eccesso è calcolato sulla "
               "media dell'universo: misura solo se gli analisti separano i migliori dai peggiori.\n"
               "- Il consenso è ricostruito dalle azioni delle banche riportate da Yahoo; una banca che non aggiorna "
               "da 12 mesi esce dal conteggio.\n")
    return "\n".join(out)


def main() -> None:
    RISULTATI.mkdir(parents=True, exist_ok=True)
    prezzi, azioni = carica()
    mancanti = giudizi_non_mappati(azioni)
    if len(mancanti):
        print("Giudizi senza punteggio (ignorati):", mancanti.head(20).to_dict())

    print("Consenso giornaliero...")
    cons = consenso_giornaliero(azioni, prezzi.index)
    ev = eventi(azioni, cons)
    print("  segnali:", ev["tipo"].value_counts().to_dict())

    print("Rendimenti in eccesso...")
    eccesso = rendimenti_in_eccesso(prezzi)
    ev_tab = studio_eventi(ev, eccesso)
    fasce, ic = studio_fasce(cons, eccesso)

    ev_tab.to_csv(RISULTATI / "eventi.csv", index=False)
    fasce.to_csv(RISULTATI / "fasce.csv", index=False)
    ic.to_csv(RISULTATI / "correlazione.csv", index=False)
    cons.to_csv(RISULTATI / "consenso_giornaliero.csv", index=False)
    (RISULTATI / "grafici.html").write_text(grafici(ev_tab, fasce), encoding="utf-8")
    (RISULTATI / "riepilogo.md").write_text(riepilogo(ev_tab, fasce, ic, cons, ev, prezzi), encoding="utf-8")
    print(f"Scritto {RISULTATI / 'riepilogo.md'}")


if __name__ == "__main__":
    main()
