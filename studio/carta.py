"""Simulazione "su carta" del piano da 2.000 €: nessun soldo reale, serve a validare la regola dal vivo.

Uso: python studio/carta.py               (aggiorna la simulazione con i prezzi di oggi e manda il messaggio Telegram)
     python studio/carta.py --messaggio   (rimanda solo l'ultimo messaggio, senza toccare la simulazione)

Regola, identica a quella del backtest (piano.py): 5 titoli a parti uguali tra quelli sopra il 90° percentile della
classifica con volatilità annua <= 50%; controllo ogni sera; si vende un titolo rimasto sotto il 40° percentile per
5 sere di fila e si compra il migliore non in portafoglio. Gli ordini decisi la sera sono eseguiti alla chiusura del
giorno di borsa successivo. Costi 2 € + 0,2% a ordine, imposta 26% sulle plusvalenze realizzate (le minusvalenze
compensano). Tutto in euro, al cambio del giorno. Confronto: gli stessi 2.000 € messi su SPY il primo giorno.

Stato in studio/carta/: stato.json (posizioni, cassa, ordini in attesa), storico.csv (un rigo per sera),
operazioni.csv (ogni acquisto e vendita). Il workflow serale li salva nel repository.
"""
import csv
import json
import re
import sys

from config import CARTELLA, RISULTATI
from telegram import invia

DIR = CARTELLA / "carta"
STATO, STORICO, OPERAZIONI = DIR / "stato.json", DIR / "storico.csv", DIR / "operazioni.csv"
K = 5
CONFERMA = 5        # sere di fila sotto soglia prima di vendere
VALUTE = {".L": ("EURGBP=X", 0.01), ".SW": ("EURCHF=X", 1.0), ".ST": ("EURSEK=X", 1.0)}   # Londra quota in pence
GIORNI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]


def num(v: float, dec: int = 0, segno: bool = False) -> str:
    t = f"{v:+,.{dec}f}" if segno else f"{v:,.{dec}f}"
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


def scrivi_riga(percorso, riga: dict) -> None:
    nuovo = not percorso.exists()
    with percorso.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(riga))
        if nuovo:
            w.writeheader()
        w.writerow(riga)


# ─── aggiornamento serale ────────────────────────────────────────────────────

def aggiorna() -> None:
    import numpy as np
    import pandas as pd
    import yfinance as yf

    from classifica import fattori, punteggi
    from piano import CAPITALE, FISSO, SOGLIA_IN, SOGLIA_OUT, SPREAD, VOL_PRUDENTE, tassa_vendita
    from prezzi_ampi import carica
    from universo_ampio import FILE_UNIVERSO_AMPIO

    close, vol = carica("prezzi_ampi"), carica("volumi_ampi")
    info = pd.read_csv(FILE_UNIVERSO_AMPIO)
    tieni = [c for c in close.columns if c in set(info["Symbol"])]
    close, vol = close[tieni].ffill(limit=3), vol[tieni]
    f = fattori(close, vol, info)
    score, _ = punteggi(f)
    pct = score.rank(axis=1, pct=True)
    oggi = close.index[-1]
    data = f"{oggi:%Y-%m-%d}"
    nomi = info.set_index("Symbol")["Nome"].to_dict()
    usa = set(info.loc[info["mercato"] == "USA", "Symbol"]) | {"SPY"}

    DIR.mkdir(exist_ok=True)
    if STATO.exists():
        st = json.loads(STATO.read_text(encoding="utf-8"))
        if st["ultima_data"] >= data:
            print(f"Simulazione già aggiornata al {st['ultima_data']}: non cambio nulla.")
            return
    else:
        st = {"inizio": data, "ultima_data": None, "cassa": CAPITALE, "capitale": CAPITALE, "credito_minus": 0.0,
              "costi": 0.0, "tasse": 0.0, "posizioni": {}, "ordini": [], "spy": None, "valore": CAPITALE, "cambi": {}}

    # cambi (unità di valuta estera per 1 euro) e SPY; se Yahoo non risponde restano gli ultimi salvati
    try:
        q = yf.download(["EURUSD=X", "SPY"] + [c for c, _ in VALUTE.values()], period="10d", auto_adjust=True,
                        progress=False)["Close"].ffill().iloc[-1]
        st["cambi"].update({k: float(v) for k, v in q.items() if pd.notna(v)})
    except Exception as err:
        print(f"Cambi non scaricati ({err}): uso gli ultimi salvati")
    cambi = st["cambi"]

    def in_euro(ticker: str, prezzo: float) -> float:
        suff = next((s for s in VALUTE if ticker.endswith(s)), None)
        if suff:
            return prezzo * VALUTE[suff][1] / cambi[VALUTE[suff][0]]
        if ticker in usa or "." not in ticker:
            return prezzo / cambi["EURUSD=X"]
        return prezzo

    def prezzo_eur(ticker: str) -> float | None:
        p = close[ticker].iloc[-1] if ticker in close.columns else np.nan
        if pd.isna(p):      # uscito dall'universo (es. capitalizzazione scesa sotto la soglia): lo chiedo a Yahoo
            try:
                p = yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1]
            except Exception:
                p = np.nan
        return None if pd.isna(p) else in_euro(ticker, float(p))

    # 1. eseguo gli ordini decisi ieri sera, ai prezzi di chiusura di oggi: prima le vendite, poi gli acquisti
    for o in [o for o in st["ordini"] if o["tipo"] == "vendi"]:
        pos = st["posizioni"].pop(o["ticker"], None)
        if pos is None:
            continue
        p = prezzo_eur(o["ticker"]) or pos["prezzo_eur"]
        lordo = pos["q"] * p
        costo = FISSO + SPREAD * lordo
        guadagno = lordo - costo - pos["costo_eur"]
        imposta, st["credito_minus"] = tassa_vendita(guadagno, st["credito_minus"])
        st["cassa"] += lordo - costo - imposta
        st["costi"] += costo
        st["tasse"] += imposta
        scrivi_riga(OPERAZIONI, {"data": data, "tipo": "vendi", "ticker": o["ticker"], "quantita": round(pos["q"], 4),
                                 "prezzo_eur": round(p, 4), "importo_eur": round(lordo, 2), "costo_eur": round(costo, 2),
                                 "imposta_eur": round(imposta, 2), "guadagno_eur": round(guadagno, 2)})
    acquisti = [o for o in st["ordini"] if o["tipo"] == "compra"]
    acquisti = [(o, prezzo_eur(o["ticker"])) for o in acquisti]
    acquisti = [(o, p) for o, p in acquisti if p]
    if acquisti and st["cassa"] >= 50:
        quota = st["cassa"] / len(acquisti)
        for o, p in acquisti:
            costo = FISSO + SPREAD * quota
            st["posizioni"][o["ticker"]] = {"nome": o["nome"], "q": (quota - costo) / p, "costo_eur": quota,
                                            "data": data, "prezzo_eur": p, "var_giorno": 0.0, "percentile": o["percentile"]}
            st["cassa"] -= quota
            st["costi"] += costo
            scrivi_riga(OPERAZIONI, {"data": data, "tipo": "compra", "ticker": o["ticker"], "quantita": round((quota - costo) / p, 4),
                                     "prezzo_eur": round(p, 4), "importo_eur": round(quota, 2), "costo_eur": round(costo, 2),
                                     "imposta_eur": 0.0, "guadagno_eur": 0.0})
        if st["spy"] is None and "SPY" in cambi:      # il confronto parte lo stesso giorno, con gli stessi costi
            st["spy"] = {"q": (CAPITALE - FISSO - SPREAD * CAPITALE) / in_euro("SPY", cambi["SPY"])}
    st["ordini"] = []

    # 2. valore di oggi
    for t, pos in st["posizioni"].items():
        p = prezzo_eur(t)
        if p:
            pos["var_giorno"] = p / pos["prezzo_eur"] - 1 if pos["data"] != data else 0.0
            pos["prezzo_eur"] = p
        pos["percentile"] = float(pct[t].iloc[-1]) if t in pct.columns and pd.notna(pct[t].iloc[-1]) else None
    valore_prec = st["valore"]
    st["valore"] = st["cassa"] + sum(p["q"] * p["prezzo_eur"] for p in st["posizioni"].values())
    if st["spy"]:
        st["spy"]["valore"] = st["spy"]["q"] * in_euro("SPY", cambi["SPY"])

    # 3. decisioni di stasera (eseguite domani): vendo chi è sotto soglia da CONFERMA sere, compro i migliori
    deboli = [t for t in st["posizioni"]
              if t not in pct.columns or not (pct[t].iloc[-CONFERMA:] >= SOGLIA_OUT).any()]
    for t in deboli:
        st["ordini"].append({"tipo": "vendi", "ticker": t, "nome": st["posizioni"][t]["nome"],
                             "percentile": st["posizioni"][t]["percentile"]})
    posti = K - (len(st["posizioni"]) - len(deboli))
    if posti > 0 and (st["cassa"] >= 50 or deboli):
        ok = f["ammesso"].iloc[-1] & (pct.iloc[-1] >= SOGLIA_IN) & ((f["volatilita_60"].iloc[-1] * np.sqrt(252)) <= VOL_PRUDENTE)
        cand = score.iloc[-1][ok].drop(labels=list(st["posizioni"]), errors="ignore").sort_values(ascending=False).head(posti)
        for t in cand.index:
            st["ordini"].append({"tipo": "compra", "ticker": t, "nome": str(nomi.get(t, t))[:40], "percentile": float(pct[t].iloc[-1])})

    st["valore_prec"], st["ultima_data"] = valore_prec, data
    scrivi_riga(STORICO, {"data": data, "valore_eur": round(st["valore"], 2), "pl_giorno_eur": round(st["valore"] - valore_prec, 2),
                          "pl_totale_eur": round(st["valore"] - st["capitale"], 2), "cassa_eur": round(st["cassa"], 2),
                          "spy_eur": round(st["spy"]["valore"], 2) if st["spy"] else "", "titoli": len(st["posizioni"]),
                          "costi_eur": round(st["costi"], 2), "tasse_eur": round(st["tasse"], 2)})
    STATO.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")


# ─── messaggio ───────────────────────────────────────────────────────────────

def verdetto() -> str:
    try:
        return re.search(r"VERDETTO DI OGGI \(.*?\): (.+)", (RISULTATI / "verdetto.md").read_text(encoding="utf-8")).group(1).strip()
    except Exception:
        return "n/d"


def messaggio() -> str:
    st = json.loads(STATO.read_text(encoding="utf-8"))
    a, m, g = (int(x) for x in st["ultima_data"].split("-"))
    from datetime import date
    giorno = date(a, m, g)
    righe = [f"📊 Simulazione su carta · {GIORNI[giorno.weekday()]} {giorno:%d/%m/%Y}", ""]
    cap = st["capitale"]
    if not st["posizioni"]:
        righe += [f"💼 Capitale: {num(st['valore'])} € (ancora in cassa)", "Nessun titolo in portafoglio: P&L 0 €."]
    else:
        pl_g, pl_t = st["valore"] - st["valore_prec"], st["valore"] - cap
        righe += [f"💼 Valore: {num(st['valore'])} €",
                  f"{'📈' if pl_g >= 0 else '📉'} Oggi: {num(pl_g, 0, True)} € ({num(100 * pl_g / st['valore_prec'], 1, True)}%)",
                  f"{'🟢' if pl_t >= 0 else '🔴'} Dall'inizio: {num(pl_t, 0, True)} € ({num(100 * pl_t / cap, 1, True)}%)"]
        if st["spy"]:
            pl_s = st["spy"]["valore"] - cap
            righe.append(f"🆚 Stessi soldi su SPY: {num(pl_s, 0, True)} € ({num(100 * pl_s / cap, 1, True)}%)")
        righe += ["", "Titoli:"]
        for t, p in sorted(st["posizioni"].items(), key=lambda kv: -kv[1]["q"] * kv[1]["prezzo_eur"]):
            val = p["q"] * p["prezzo_eur"]
            tot = val / p["costo_eur"] - 1
            perc = f"{100 * p['percentile']:.0f}°" if p["percentile"] is not None else "fuori classifica"
            righe.append(f"{'🟢' if tot >= 0 else '🔴'} {t}: {num(val)} € · oggi {num(100 * p['var_giorno'], 1, True)}% · "
                         f"totale {num(100 * tot, 1, True)}% · {perc}")
        if st["cassa"] >= 1:
            righe.append(f"💶 Cassa: {num(st['cassa'])} €")
    righe.append("")
    if st["ordini"]:
        righe.append("🔔 Ordini per la prossima seduta:")
        for o in st["ordini"]:
            perc = f"{100 * o['percentile']:.0f}° percentile" if o["percentile"] is not None else "fuori classifica"
            righe.append(f"  {'🛒 COMPRA' if o['tipo'] == 'compra' else '💸 VENDI'} {o['ticker']} ({o['nome']}) · {perc}")
    else:
        righe.append("😴 Nessuna operazione da fare.")
    righe += [f"🚦 Mercato: {verdetto()}", "", "🧪 Solo simulazione: nessun soldo reale."]
    return "\n".join(righe)


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if "--messaggio" not in sys.argv:
        aggiorna()
    testo = messaggio()
    print(testo)
    invia(testo)
