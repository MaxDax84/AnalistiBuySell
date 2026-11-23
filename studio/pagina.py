"""Genera la pagina web con i grafici: docs/index.html (pubblicata da GitHub Pages).

Uso: python studio/pagina.py
Legge data/regime.csv e i file in risultati/. Nessun dato sensibile: solo serie pubbliche di mercato.
"""

import json
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go

from config import CARTELLA, RISULTATI
from regime import FILE_REGIME, segnali, semaforo
from verdetto import verdetti

USCITA = CARTELLA.parent / "docs" / "index.html"
COLORI = {"STRONG BUY": "#1b7f3b", "BUY": "#7cc47f", "WAIT": "#c9c9c9", "SMALL SELL": "#d9534f"}
CFG = {"displayModeBar": False, "responsive": True}
LAYOUT = dict(margin=dict(l=40, r=20, t=50, b=40), paper_bgcolor="white", plot_bgcolor="white",
              font=dict(family="system-ui, -apple-system, Segoe UI, Roboto, sans-serif", size=13),
              legend=dict(orientation="h", y=-0.2))


def fig_html(fig: go.Figure) -> str:
    fig.update_layout(**LAYOUT)
    fig.update_xaxes(gridcolor="#eee")
    fig.update_yaxes(gridcolor="#eee")
    return fig.to_html(include_plotlyjs=False, full_html=False, config=CFG)


def grafico_indice(s: pd.DataFrame) -> str:
    u = s.loc[s.index >= s.index[-1] - pd.DateOffset(years=3)]
    fig = go.Figure()
    # fasce colorate per verdetto (giorni consecutivi uguali = una fascia)
    blocchi = (u["verdetto"] != u["verdetto"].shift()).cumsum()
    for _, g in u.groupby(blocchi):
        v = g["verdetto"].iloc[0]
        if v != "WAIT":
            fig.add_vrect(x0=g.index[0], x1=g.index[-1] + pd.Timedelta(days=1), fillcolor=COLORI[v], opacity=0.25, line_width=0)
    fig.add_trace(go.Scatter(x=u.index, y=u["SP"], name="S&P 500", line=dict(color="#1f3b73", width=2)))
    fig.add_trace(go.Scatter(x=u.index, y=u["mm200"], name="media 200 giorni", line=dict(color="#888", dash="dot", width=1)))
    for v in ["STRONG BUY", "BUY", "SMALL SELL"]:
        fig.add_trace(go.Bar(x=[None], y=[None], name=v, marker_color=COLORI[v], opacity=0.5))
    fig.update_layout(title="S&P 500 negli ultimi 3 anni, con i verdetti del giorno colorati", height=420)
    return fig_html(fig)


def grafico_verdetti(storico: pd.DataFrame) -> str:
    fig = go.Figure()
    colonne = [("3 mesi: vs sempre investito", "dopo 3 mesi", "#9ec5e8"), ("6 mesi: vs sempre investito", "dopo 6 mesi", "#4a90c8"),
               ("12 mesi: vs sempre investito", "dopo 12 mesi", "#1f3b73")]
    for col, nome, colore in colonne:
        fig.add_trace(go.Bar(x=storico["verdetto"], y=storico[col], name=nome, marker_color=colore, cliponaxis=False,
                             text=[f"{v:+.1f}%" for v in storico[col]], textposition="outside"))
    valori = storico[[c for c, _, _ in colonne]]
    fig.update_layout(title="Cosa ha fatto l'S&P 500 dopo ogni verdetto, dal 1990 (in più o in meno rispetto allo stare sempre investito)",
                      barmode="group", height=420, yaxis=dict(title="%", range=[valori.min().min() * 1.35, valori.max().max() * 1.35]))
    return fig_html(fig)


def grafico_paura(s: pd.DataFrame) -> str:
    u = s.loc[s.index >= s.index[-1] - pd.DateOffset(years=3)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=u.index, y=u["VIX"], name="VIX (paura)", line=dict(color="#b03a2e")))
    fig.add_hline(y=30, line_dash="dash", line_color="#1b7f3b", annotation_text="30 = panico: storicamente momento di comprare")
    fig.add_hline(y=20, line_dash="dot", line_color="#999", annotation_text="20")
    fig.update_layout(title="Paura (VIX) negli ultimi 3 anni", height=320)
    return fig_html(fig)


def grafico_credito(s: pd.DataFrame) -> str:
    u = s.loc[s.index >= s.index[-1] - pd.DateOffset(years=3)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=u.index, y=100 * u["hyg_var"], name="HYG, variazione 60 gg (%)", line=dict(color="#8e44ad"),
                             fill="tozeroy"))
    fig.add_hline(y=-3, line_dash="dash", line_color="#d9534f", annotation_text="-3%: credito in stress (allarme)")
    fig.add_hline(y=-6, line_dash="dash", line_color="#1b7f3b", annotation_text="-6%: capitolazione (comprare)")
    fig.update_layout(title="Stress del credito: obbligazioni ad alto rendimento (HYG) negli ultimi 3 anni", height=320)
    return fig_html(fig)


def grafico_strategie(strat: pd.DataFrame) -> str:
    fig = go.Figure()
    fig.add_trace(go.Bar(y=strat["regola"], x=strat["rendimento_annuo_%"], orientation="h", name="rendimento annuo %",
                         marker_color="#1f3b73", text=[f"{v:.1f}%" for v in strat["rendimento_annuo_%"]], textposition="outside"))
    fig.add_trace(go.Bar(y=strat["regola"], x=strat["peggior_calo_%"], orientation="h", name="peggior calo %",
                         marker_color="#d9534f", text=[f"{v:.0f}%" for v in strat["peggior_calo_%"]], textposition="outside"))
    fig.update_layout(title="Regole di uscita dal mercato, 1991-oggi: quanto rendono e quanto si perde nel momento peggiore",
                      barmode="overlay", height=460, xaxis_title="%", yaxis=dict(autorange="reversed"))
    return fig_html(fig)


def grafico_liquidita(piano: pd.DataFrame) -> str:
    fig = go.Figure(go.Bar(x=piano["valore_finale_€"] / 1e6, y=piano["politica"], orientation="h", marker_color="#1b7f3b",
                           text=[f"{v / 1e6:.2f} M€" for v in piano["valore_finale_€"]], textposition="outside"))
    fig.update_layout(title="1.000 € al mese per 36 anni (443.000 € versati): quanto valgono oggi secondo la politica di ingresso",
                      height=380, xaxis_title="milioni di €", yaxis=dict(autorange="reversed"))
    return fig_html(fig)


def grafico_analisti(eventi: pd.DataFrame) -> str:
    fig = go.Figure()
    colori = {"banca: alza": "#1b7f3b", "banca: abbassa": "#d9534f", "consenso: Tieni -> Compra": "#7cc47f",
              "consenso: Compra -> Tieni": "#e59866"}
    for tipo, c in colori.items():
        g = eventi[(eventi["segnale"] == tipo) & (eventi["orizzonte_gg"] > 0)]
        fig.add_trace(go.Scatter(x=g["orizzonte_gg"], y=g["eccesso_medio_%"], name=tipo, line=dict(color=c), mode="lines+markers"))
    fig.add_hline(y=0, line_color="#999")
    fig.update_layout(title="Dopo un giudizio degli analisti: rendimento del titolo oltre la media, nei giorni successivi (S&P 500, 5 anni)",
                      height=400, xaxis=dict(title="giorni di borsa dopo il segnale", type="log"), yaxis_title="%")
    return fig_html(fig)


def sezione_classifica() -> str:
    """Tabella dei primi 25 titoli della classifica ampia e grafico delle 10 fasce del backtest (se esistono)."""
    f_oggi, f_fasce = RISULTATI / "classifica_oggi.csv", RISULTATI / "classifica_fasce.csv"
    if not f_oggi.exists():
        return ""
    oggi = pd.read_csv(f_oggi)
    # tutti i titoli vanno nella pagina come dati: la tabella mostra i primi 25, la casella di ricerca trova gli altri
    titoli = [[i + 1, r["Ticker"], str(r["Nome"])[:38], r["mercato"], round(r["prezzo"], 2), round(r["rend_12m_%"]),
               round(r["rend_1m_%"]), round(r["volatilita_annua_%"]), round(r["dal_max_52_%"]), round(r["percentile"])]
              for i, (_, r) in enumerate(oggi.fillna({"prezzo": 0, "rend_12m_%": 0, "rend_1m_%": 0, "volatilita_annua_%": 0,
                                                      "dal_max_52_%": 0, "percentile": 0}).iterrows())]
    dati_js = json.dumps(titoli, allow_nan=False, default=str).replace("</", "<\\/")
    tabella = """<input id="cerca" type="search" placeholder="Cerca un titolo per sigla o nome (es. ENI, Apple, ASML)"
    style="width:100%;box-sizing:border-box;padding:.6em .8em;font-size:1rem;border:1px solid #ccc;border-radius:8px;margin:.4em 0">
    <p class="nota" id="esito"></p>
    <table class="tab"><thead><tr><th>#</th><th>titolo</th><th>mercato</th><th>prezzo</th><th>12 mesi</th><th>1 mese</th>
    <th>volatilità</th><th>dal max 52 sett.</th><th>percentile</th></tr></thead><tbody id="righe"></tbody></table>
    <script>
    const TITOLI = """ + dati_js + """;
    const segno = v => (v > 0 ? "+" : "") + v + "%";
    const esc = t => String(t).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
    function mostra() {
      const q = document.getElementById("cerca").value.trim().toLowerCase();
      const trovati = q ? TITOLI.filter(r => r[1].toLowerCase().includes(q) || r[2].toLowerCase().includes(q)) : TITOLI.slice(0, 25);
      document.getElementById("righe").innerHTML = trovati.slice(0, 50).map(r =>
        `<tr><td>${r[0]}</td><td><b>${esc(r[1])}</b><br><small>${esc(r[2])}</small></td><td>${esc(r[3])}</td><td>${r[4].toFixed(2)}</td>` +
        `<td>${segno(r[5])}</td><td>${segno(r[6])}</td><td>${r[7]}%</td><td>${segno(r[8])}</td><td>${r[9]}°</td></tr>`).join("");
      document.getElementById("esito").textContent = !q ? "I primi 25 di " + TITOLI.length + " titoli." :
        trovati.length === 0 ? "Nessun titolo trovato: forse non è nell'elenco (troppo piccolo, o borsa non coperta)." :
        trovati.length === 1 ? "1 titolo trovato." :
        trovati.length + " titoli trovati" + (trovati.length > 50 ? ": mostro i primi 50." : ".");
    }
    document.getElementById("cerca").addEventListener("input", mostra);
    mostra();
    </script>"""
    grafico = ""
    if f_fasce.exists():
        fasce = pd.read_csv(f_fasce)
        fig = go.Figure(go.Bar(x=[f"F{i}" for i in range(1, 11)], y=fasce["vs_universo_annuo_%"],
                               marker_color=["#d9534f"] * 3 + ["#c9c9c9"] * 4 + ["#1b7f3b"] * 3,
                               text=[f"{v:+.1f}%" for v in fasce["vs_universo_annuo_%"]], textposition="outside", cliponaxis=False))
        fig.update_layout(title="Backtest 5 anni: rendimento annuo di ogni fascia rispetto alla media di tutti i titoli (F1 = punteggio peggiore, F10 = migliore)",
                          height=380, yaxis_title="% annuo vs universo")
        grafico = f'<div class="card">{fig_html(fig)}<p class="nota">Se la classifica funziona, le barre devono salire da sinistra a destra: F10 sopra lo zero, F1 sotto. Costi non inclusi in questo grafico; nel rapporto completo sì.</p></div>'
    return f"""
<h2>Classifica di tutte le azioni comprabili ({len(oggi)} titoli)</h2>
<div class="card">
<p class="nota">Ogni sera tutti i titoli USA con capitalizzazione &gt; 1 mld $ e le grandi e medie europee (Italia, Germania, Francia, Spagna, Paesi Bassi, Belgio, Svizzera, Regno Unito, Svezia) vengono ordinati con quattro fattori: momentum a 12 mesi, inversione dell'ultimo mese, bassa volatilità, vicinanza al massimo annuale. Qui sotto i 25 in cima; con la casella di ricerca trovi la posizione di qualsiasi titolo (il percentile dice quanti titoli ha dietro: 90° = meglio del 90%). Non è una lista della spesa: è dove, storicamente, le probabilità sono un po' più alte. Dettagli e portafoglio in <a href="https://github.com/MaxDax84/AnalistiBuySell/blob/master/studio/risultati/classifica.md">classifica.md</a>.</p>
{tabella}
</div>
{grafico}"""


def chip(testo: str, ok: bool | None) -> str:
    colore = {True: "#1b7f3b", False: "#d9534f", None: "#999"}[ok]
    return f'<span class="chip" style="border-color:{colore}"><span class="dot" style="background:{colore}"></span>{testo}</span>'


def condizioni_oggi(s: pd.DataFrame) -> str:
    u = s.iloc[-1]
    voci = [
        ("Tendenza: " + u["trend"], u["trend"] == "sopra MM200"),
        ("Momentum: " + u["mom12"], u["mom12"] == "12 mesi positivi"),
        (f"Paura: VIX {u['VIX']:.0f}", u["VIX"] < 30),
        ("Credito: " + u["credito"], u["hyg_var"] > -0.03 if pd.notna(u["hyg_var"]) else None),
        ("Lavoro: " + u["lavoro"], u["claims_var"] < 0.10),
        ("Incertezza politica: " + u["incertezza"], u["epu_pct"] < 0.9),
        ("Geopolitica: " + u.get("geopolitica", "n/d"), None),
        (f"Indice {100 * u['dd']:+.1f}% dal massimo di 1 anno", None),
        ("Curva dei tassi: " + u["curva_stato"], None),
    ]
    return "".join(chip(t, ok) for t, ok in voci)


def pagina(s, storico, strat, piano, eventi) -> str:
    u = s.iloc[-1]
    v = u["verdetto"]
    spiegazione = {
        "STRONG BUY": "Panico o capitolazione. Dal 1990, dopo questi giorni l'indice ha fatto in media +7% in più del solito a 12 mesi, in tutti e 4 i decenni. È il momento in cui tutto sembra sbagliato: per questo la regola è stata scritta prima, a mente fredda.",
        "BUY": "Un calo ordinario (5-10% dal massimo) con il mercato ancora in salute, oppure incertezza politica estrema. Storicamente: +2,5% oltre la norma nei mesi dopo, positivo 8 volte su 10.",
        "WAIT": "Nessuna occasione particolare: il mercato è vicino ai massimi o in una fase senza segnali. Si continua con le tranche ordinarie, niente di più. È il verdetto del 62% dei giorni.",
        "SMALL SELL": "Allarme: momentum negativo, credito in stress, o un calo tra il 10 e il 20% con paura in aumento. Storicamente: −6% a 6 mesi rispetto alla norma. Si riduce un po', non si vende tutto, e non si investe liquidità nuova finché non cambia.",
    }[v]
    ultimi = s["verdetto"].tail(60)
    striscia = "".join(f'<span class="giorno" title="{d:%d/%m}" style="background:{COLORI[x]}"></span>' for d, x in ultimi.items())
    return f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Semaforo di mercato</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
 body{{margin:0;background:#f6f7f9;color:#222;font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.5}}
 main{{max-width:1000px;margin:0 auto;padding:16px}}
 h1{{font-size:1.6rem;margin:.2em 0}} h2{{font-size:1.2rem;margin:1.6em 0 .4em}}
 .verdetto{{display:inline-block;padding:.35em 1em;border-radius:12px;color:#fff;font-weight:700;font-size:2rem;background:{COLORI[v]};{'color:#222;' if v == 'WAIT' else ''}}}
 .card{{background:#fff;border-radius:12px;padding:14px 16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
 .chip{{display:inline-flex;align-items:center;gap:.4em;border:1.5px solid;border-radius:999px;padding:.15em .7em;margin:.2em .3em .2em 0;font-size:.92rem;background:#fff}}
 .dot{{width:.65em;height:.65em;border-radius:50%}}
 .striscia{{display:flex;gap:2px;margin:.4em 0}} .giorno{{flex:1;height:18px;border-radius:2px}}
 p.nota{{color:#555;font-size:.95rem}} small{{color:#777}}
 .tab{{width:100%;border-collapse:collapse;font-size:.9rem}} .tab th,.tab td{{padding:.35em .5em;border-bottom:1px solid #eee;text-align:right}}
 .tab th:nth-child(2),.tab td:nth-child(2){{text-align:left}} .tab thead th{{color:#555;font-weight:600}}
</style></head><body><main>
<h1>Semaforo di mercato</h1>
<p class="nota">Aggiornato il {s.index[-1]:%d/%m/%Y} (dati alla chiusura di Wall Street). Regole fisse, verificate dal 1990; nessuna lettura delle notizie del giorno. Non è un consiglio d'investimento: è uno strumento per decidere con la testa fredda.</p>

<div class="card">
 <div>Verdetto di oggi</div>
 <div class="verdetto">{v}</div>
 <p>{spiegazione}</p>
 <div>Ultimi 60 giorni di borsa:</div>
 <div class="striscia">{striscia}</div>
 <h2 style="margin-top:.8em">Le condizioni di oggi</h2>
 <div>{condizioni_oggi(s)}</div>
 <p class="nota">Verde = favorevole, rosso = sfavorevole, grigio = solo contesto. S&P 500 a {u['SP']:,.0f}, VIX {u['VIX']:.1f}, {int(u['punti'])} condizioni favorevoli su 6.</p>
</div>

<div class="card">{grafico_indice(s)}
<p class="nota">Le fasce verdi sono i giorni in cui le regole dicevano di comprare, quelle rosse i giorni di allarme. Guarda cosa ha fatto la linea blu nei mesi dopo ogni fascia: è il modo più onesto di giudicare il semaforo.</p></div>

<div class="card">{grafico_verdetti(storico)}
<p class="nota">Barre sopra lo zero = dopo quel verdetto il mercato ha fatto meglio del solito. STRONG BUY e BUY sono coerenti in tutti e 4 i decenni; SMALL SELL in 2 su 4. WAIT è, come deve essere, la normalità.</p></div>

<h2>I due termometri che contano di più</h2>
<div class="card">{grafico_paura(s)}</div>
<div class="card">{grafico_credito(s)}
<p class="nota">Il credito è l'allarme precoce: quando le obbligazioni rischiose scendono del 3-6% in due mesi, nei 6 mesi dopo l'indice ha fatto −8% rispetto alla norma. Quando crollano oltre il 6%, è capitolazione: da lì +14% a 12 mesi.</p></div>

<h2>Perché il semaforo non dice mai "vendi tutto"</h2>
<div class="card">{grafico_strategie(strat)}
<p class="nota">Stare sempre investiti ha reso il 9,1% l'anno dal 1991, ma con un calo massimo del 57%. Ogni regola di uscita rende meno; la migliore (uscire quando i 12 mesi sono negativi) costa 0,7 punti l'anno e dimezza il calo peggiore. Uscire quando la paura è alta è la cosa peggiore: si vende sul fondo.</p></div>

<h2>E la liquidità nuova?</h2>
<div class="card">{grafico_liquidita(piano)}
<p class="nota">Aspettare i verdetti buoni per investire la liquidità costa più di quanto renda, perché il mercato sale anche nei giorni di WAIT. La liquidità nuova va investita a scadenze fisse; il verdetto serve a non fermarsi (anzi aggiungere) nel panico e a ridurre un po' negli allarmi.</p></div>

{sezione_classifica()}

<h2>E i giudizi degli analisti?</h2>
<div class="card">{grafico_analisti(eventi)}
<p class="nota">Tutte le linee stanno attorno allo zero: dopo un "compra" o un "vendi" degli analisti, nei giorni e mesi successivi non resta nulla da prendere. La reazione avviene nel giorno stesso dell'annuncio (+1,8% per un upgrade), prima che si possa agire.</p></div>

<p><small>Fonti: Yahoo Finance (S&P 500, VIX, HYG, giudizi degli analisti), FRED (curva dei tassi, sussidi), policyuncertainty.com (EPU), Caldara-Iacoviello (GPR). Codice e dati: <a href="https://github.com/MaxDax84/AnalistiBuySell/tree/master/studio">github.com/MaxDax84/AnalistiBuySell</a>. Generato il {datetime.now():%d/%m/%Y %H:%M}.</small></p>
</main></body></html>"""


def main():
    df = pd.read_csv(FILE_REGIME, index_col=0, parse_dates=True)
    s = segnali(df)
    s["semaforo"], s["punti"] = semaforo(s)
    s["verdetto"] = verdetti(s)
    storico = pd.read_csv(RISULTATI / "verdetto_storico.csv")
    strat = pd.read_csv(RISULTATI / "regime_strategie.csv")
    eventi = pd.read_csv(RISULTATI / "eventi.csv")
    from verdetto import piano_liquidita
    piano = piano_liquidita(s)
    USCITA.parent.mkdir(parents=True, exist_ok=True)
    USCITA.write_text(pagina(s, storico, strat, piano, eventi), encoding="utf-8")
    print(f"Scritto {USCITA} ({USCITA.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
