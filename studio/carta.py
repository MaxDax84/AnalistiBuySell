"""Simulazione "su carta" del piano da 2.000 €: nessun soldo reale, serve a validare le regole dal vivo.

Uso: python studio/carta.py               (aggiorna i portafogli con i prezzi di oggi e manda il messaggio Telegram)
     python studio/carta.py --messaggio   (rimanda solo l'ultimo messaggio, senza toccare la simulazione)

Più portafogli da 2.000 € corrono in parallelo, uno per regola (vedi PORTAFOGLI e modelli.py), così le idee si
confrontano sugli stessi giorni. Per tutti: 5 titoli a parti uguali tra quelli sopra il 90° percentile; controllo
ogni sera; si vende un titolo rimasto sotto il 40° percentile per 5 sere di fila e si compra il migliore non in
portafoglio. Gli ordini decisi la sera sono eseguiti alla chiusura del giorno di borsa successivo. Costi 2 € + 0,2%
a ordine, imposta 26% sulle plusvalenze realizzate (le minusvalenze compensano). Tutto in euro, al cambio del giorno.
Confronto: gli stessi 2.000 € messi sull'ETF iShares Core MSCI World (SWDA, in euro) il giorno del primo acquisto.

Ogni settimana parte un nuovo gruppo di portafogli (carta/AAAA-MM-GG/): con più date di partenza il confronto tra
le regole dipende meno dalla fortuna di un singolo giorno. Partenze vicine comprano quasi gli stessi titoli: non
sono prove indipendenti. Il messaggio mostra in dettaglio il primo gruppo e la media di tutte le partenze.

Stato in studio/carta/<AAAA-MM-GG>/<portafoglio>/: stato.json (posizioni, cassa, ordini in attesa), storico.csv (un rigo per
sera), operazioni.csv (ogni acquisto e vendita). Il workflow serale li salva nel repository.
"""
import csv
import json
import re
import sys
from datetime import date

from config import CARTELLA, RISULTATI
from telegram import invia

DIR = CARTELLA / "carta"
K = 5
CONFERMA = 5        # sere di fila sotto soglia prima di vendere
MAX_GRUPPI = 52     # partenze settimanali: una a settimana per un anno
COPERTURA_MINIMA = 0.9   # sotto questa quota di titoli con prezzi la serata si salta
N_REVISIONI = 60    # di quanti candidati si salvano ogni sera le revisioni degli utili
VALUTE = {".L": ("EURGBP=X", 0.01), ".SW": ("EURCHF=X", 1.0), ".ST": ("EURSEK=X", 1.0)}   # Londra quota in pence
GIORNI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
NUMERI = "①②③④⑤"
NOME_RIF = "MSCI World"      # iShares Core MSCI World (SWDA.MI): vedi RIFERIMENTO in modelli.py
PRUDENTE = {"universo": "data", "segnale": "pulito", "corr_max": 0.5, "freno": True}     # = "tutto insieme" di modelli.py
PORTAFOGLI = {
    "base": {"etichetta": "Base (la regola del backtest)", "modello": {}},
    "prudente": {"etichetta": "Regolari (salita regolare, niente gemelli, freno di mercato)", "modello": PRUDENTE},
    "utili": {"etichetta": "Regolari + utili attesi in rialzo", "modello": {**PRUDENTE, "utili": True}},
}


def gruppi() -> list[str]:
    """Partenze già avviate (cartelle carta/AAAA-MM-GG, la data del primo segnale), dalla più vecchia."""
    return sorted(c.name for c in DIR.glob("*") if c.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", c.name))


def settimana(giorno: str) -> tuple[int, int]:
    return date.fromisoformat(giorno).isocalendar()[:2]


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

def aggiorna() -> str:
    """Aggiorna tutti i portafogli. Ritorna un avviso (stringa vuota se tutto bene)."""
    import numpy as np
    import pandas as pd
    import yfinance as yf

    from modelli import RIFERIMENTO, dati, freno_mercato, opzioni, punteggio, scarica_cambi, scegli
    from piano import CAPITALE, FISSO, SOGLIA_IN, SOGLIA_OUT, SPREAD, tassa_vendita
    from revisioni import raccogli

    larga = dati("data")                    # tutti i titoli scaricati: da qui si leggono i prezzi
    close, info = larga["close"], larga["info"]
    data = f"{close.index[-1]:%Y-%m-%d}"
    nomi = info.set_index("Symbol")["Nome"].to_dict()
    usa = set(info.loc[info["mercato"] == "USA", "Symbol"])
    DIR.mkdir(exist_ok=True)

    # Con dati incompleti la classifica è sbagliata e gli acquisti saltano: meglio fermarsi una sera che simulare male.
    copertura = len(close.columns) / len(info)
    if copertura < COPERTURA_MINIMA:
        return f"⚠️ Stasera Yahoo ha dato i prezzi solo del {100 * copertura:.0f}% dei titoli: simulazione non aggiornata."
    try:      # cambi (unità di valuta estera per 1 euro) e ETF di riferimento, alla data dei prezzi
        cambi = scarica_cambi("1mo").loc[:data].iloc[-1].to_dict()
    except Exception as err:
        return f"⚠️ Cambi ed ETF di riferimento non disponibili stasera ({err}): simulazione non aggiornata."
    (DIR / "cambi.json").write_text(json.dumps({"data": data, **cambi}, indent=1), encoding="utf-8")
    try:
        freno_oggi = bool(freno_mercato(close.index)[-1])
    except Exception as err:
        print(f"Verdetto di mercato non disponibile ({err}): nessun freno")
        freno_oggi = False

    def in_euro(ticker: str, prezzo: float) -> float:
        suff = next((s for s in VALUTE if ticker.endswith(s)), None)
        if suff:
            return prezzo * VALUTE[suff][1] / cambi[VALUTE[suff][0]]
        if ticker in usa or "." not in ticker:
            return prezzo / cambi["EURUSD=X"]
        return prezzo

    def prezzo_eur(ticker: str) -> float | None:
        p = close[ticker].iloc[-1] if ticker in close.columns else np.nan
        if pd.isna(p):      # uscito dall'universo: lo chiedo a Yahoo
            try:
                p = yf.Ticker(ticker).history(period="5d")["Close"].iloc[-1]
            except Exception:
                p = np.nan
        return None if pd.isna(p) else in_euro(ticker, float(p))

    avviati = gruppi()
    if not avviati or (settimana(data) > settimana(avviati[-1]) and len(avviati) < MAX_GRUPPI):
        avviati.append(data)            # primo giorno di borsa di una settimana nuova: parte un altro gruppo
    for gruppo, nome, cfg in [(g, n, c) for g in avviati for n, c in PORTAFOGLI.items()]:
        cartella = DIR / gruppo / nome
        cartella.mkdir(parents=True, exist_ok=True)
        f_stato, f_storico, f_oper = cartella / "stato.json", cartella / "storico.csv", cartella / "operazioni.csv"
        if f_stato.exists():
            st = json.loads(f_stato.read_text(encoding="utf-8"))
            if st["ultima_data"] >= data:
                print(f"[{gruppo}/{nome}] già aggiornato al {st['ultima_data']}: non cambio nulla.")
                continue
        else:
            st = {"inizio": data, "ultima_data": None, "cassa": CAPITALE, "capitale": CAPITALE, "credito_minus": 0.0,
                  "costi": 0.0, "tasse": 0.0, "posizioni": {}, "ordini": [], "rif": None, "valore": CAPITALE}
        o = opzioni(cfg["modello"])
        d = dati(o["universo"])
        score = punteggio(d, o["segnale"])
        pct = score.rank(axis=1, pct=True)
        colonne = list(d["close"].columns)

        # 1. eseguo gli ordini decisi ieri sera, ai prezzi di chiusura di oggi: prima le vendite, poi gli acquisti
        for ordine in [x for x in st["ordini"] if x["tipo"] == "vendi"]:
            pos = st["posizioni"].pop(ordine["ticker"], None)
            if pos is None:
                continue
            p = prezzo_eur(ordine["ticker"]) or pos["prezzo_eur"]
            lordo = pos["q"] * p
            costo = FISSO + SPREAD * lordo
            guadagno = lordo - costo - pos["costo_eur"]
            imposta, st["credito_minus"] = tassa_vendita(guadagno, st["credito_minus"])
            st["cassa"] += lordo - costo - imposta
            st["costi"] += costo
            st["tasse"] += imposta
            scrivi_riga(f_oper, {"data": data, "tipo": "vendi", "ticker": ordine["ticker"], "quantita": round(pos["q"], 4),
                                 "prezzo_eur": round(p, 4), "importo_eur": round(lordo, 2), "costo_eur": round(costo, 2),
                                 "imposta_eur": round(imposta, 2), "guadagno_eur": round(guadagno, 2)})
        acquisti = [(x, prezzo_eur(x["ticker"])) for x in st["ordini"] if x["tipo"] == "compra"]
        # un acquisto senza prezzo stasera resta in attesa (fino a 3 sere) e la sua parte di cassa non si tocca
        in_attesa = [{**x, "tentativi": x.get("tentativi", 0) + 1} for x, p in acquisti if not p and x.get("tentativi", 0) < 2]
        acquisti = [(x, p) for x, p in acquisti if p]
        if acquisti and st["cassa"] >= 50:
            quota = st["cassa"] / (len(acquisti) + len(in_attesa))
            for ordine, p in acquisti:
                costo = FISSO + SPREAD * quota
                st["posizioni"][ordine["ticker"]] = {"nome": ordine["nome"], "q": (quota - costo) / p, "costo_eur": quota, "data": data,
                                                     "prezzo_eur": p, "var_giorno": 0.0, "percentile": ordine["percentile"]}
                st["cassa"] -= quota
                st["costi"] += costo
                scrivi_riga(f_oper, {"data": data, "tipo": "compra", "ticker": ordine["ticker"], "quantita": round((quota - costo) / p, 4),
                                     "prezzo_eur": round(p, 4), "importo_eur": round(quota, 2), "costo_eur": round(costo, 2),
                                     "imposta_eur": 0.0, "guadagno_eur": 0.0})
            if st["rif"] is None:      # il confronto parte lo stesso giorno, con gli stessi costi
                st["rif"] = {"q": (CAPITALE - FISSO - SPREAD * CAPITALE) / cambi[RIFERIMENTO]}
        st["ordini"] = in_attesa

        # 2. valore di oggi
        for t, pos in st["posizioni"].items():
            p = prezzo_eur(t)
            if p:
                pos["var_giorno"] = p / pos["prezzo_eur"] - 1 if pos["data"] != data else 0.0
                pos["prezzo_eur"] = p
            pos["percentile"] = float(pct[t].iloc[-1]) if t in pct.columns and pd.notna(pct[t].iloc[-1]) else None
        valore_prec = st["valore"]
        st["valore"] = st["cassa"] + sum(p["q"] * p["prezzo_eur"] for p in st["posizioni"].values())
        if st["rif"]:
            st["rif"]["valore"] = st["rif"]["q"] * cambi[RIFERIMENTO]

        # 3. decisioni di stasera (eseguite domani): vendo chi è sotto soglia da CONFERMA sere, compro i migliori
        deboli = [t for t in st["posizioni"] if t not in pct.columns or not (pct[t].iloc[-CONFERMA:] >= SOGLIA_OUT).any()]
        for t in deboli:
            st["ordini"].append({"tipo": "vendi", "ticker": t, "nome": st["posizioni"][t]["nome"],
                                 "percentile": st["posizioni"][t]["percentile"]})
        tenuti = [t for t in st["posizioni"] if t not in deboli]
        ok = d["f"]["ammesso"].iloc[-1] & (pct.iloc[-1] >= SOGLIA_IN)
        if o["vol_max"]:
            ok &= (d["f"]["volatilita_60"].iloc[-1] * np.sqrt(252)) <= o["vol_max"]
        attesi = [x["ticker"] for x in in_attesa]
        cand = list(score.iloc[-1][ok].drop(labels=list(st["posizioni"]) + attesi, errors="ignore").sort_values(ascending=False).index)
        st["nota"] = ""
        if o["utili"]:
            rev = raccogli(cand[:N_REVISIONI], data)       # salvate ogni sera: tra qualche mese si potranno misurare
            cand = [t for t in cand[:N_REVISIONI] if rev.get(t, 0) > 0]
        posti = K - len(tenuti) - len(attesi)
        if posti > 0 and (st["cassa"] >= 50 or deboli):
            if o["freno"] and freno_oggi:
                st["nota"] = "freno di mercato (SMALL SELL): nessun nuovo acquisto"
            else:
                scelti = scegli([colonne.index(t) for t in cand], [colonne.index(t) for t in tenuti + attesi if t in colonne], posti,
                                d["r"].values, len(d["close"]) - 1, o["corr_max"])
                for j in scelti:
                    t = colonne[j]
                    st["ordini"].append({"tipo": "compra", "ticker": t, "nome": str(nomi.get(t, t))[:40], "percentile": float(pct[t].iloc[-1])})

        st["valore_prec"], st["ultima_data"] = valore_prec, data
        scrivi_riga(f_storico, {"data": data, "valore_eur": round(st["valore"], 2), "pl_giorno_eur": round(st["valore"] - valore_prec, 2),
                                "pl_totale_eur": round(st["valore"] - st["capitale"], 2), "cassa_eur": round(st["cassa"], 2),
                                "riferimento_eur": round(st["rif"]["valore"], 2) if st["rif"] else "", "titoli": len(st["posizioni"]),
                                "costi_eur": round(st["costi"], 2), "tasse_eur": round(st["tasse"], 2)})
        f_stato.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")
    return ""


# ─── messaggio ───────────────────────────────────────────────────────────────

def verdetto() -> str:
    try:
        return re.search(r"VERDETTO DI OGGI \(.*?\): (.+)", (RISULTATI / "verdetto.md").read_text(encoding="utf-8")).group(1).strip()
    except Exception:
        return "n/d"


def blocco(i: int, etichetta: str, st: dict) -> list[str]:
    cap = st["capitale"]
    righe = [f"{NUMERI[i]} {etichetta}"]
    if not st["posizioni"]:
        righe.append(f"💼 {num(st['valore'])} € in cassa · P&L 0 €")
    else:
        pl_g, pl_t = st["valore"] - st["valore_prec"], st["valore"] - cap
        righe += [f"💼 Valore: {num(st['valore'])} €",
                  f"{'📈' if pl_g >= 0 else '📉'} Oggi: {num(pl_g, 0, True)} € ({num(100 * pl_g / st['valore_prec'], 1, True)}%)",
                  f"{'🟢' if pl_t >= 0 else '🔴'} Dall'inizio: {num(pl_t, 0, True)} € ({num(100 * pl_t / cap, 1, True)}%)"]
        if st["rif"]:
            pl_s = st["rif"]["valore"] - cap
            righe.append(f"🆚 Stessi soldi su {NOME_RIF}: {num(pl_s, 0, True)} € ({num(100 * pl_s / cap, 1, True)}%)")
        for t, p in sorted(st["posizioni"].items(), key=lambda kv: -kv[1]["q"] * kv[1]["prezzo_eur"]):
            tot = p["q"] * p["prezzo_eur"] / p["costo_eur"] - 1
            perc = f"{100 * p['percentile']:.0f}°" if p["percentile"] is not None else "fuori classifica"
            righe.append(f"  {'🟢' if tot >= 0 else '🔴'} {t}: oggi {num(100 * p['var_giorno'], 1, True)}% · "
                         f"totale {num(100 * tot, 1, True)}% · {perc}")
        if st["cassa"] >= 1:
            righe.append(f"  💶 Cassa: {num(st['cassa'])} €")
    for o in st["ordini"]:
        righe.append(f"  {'🛒 COMPRA' if o['tipo'] == 'compra' else '💸 VENDI'} {o['ticker']} ({o['nome']})"
                     + (" · in attesa del prezzo" if o.get("tentativi") else ""))
    if st.get("nota"):
        righe.append(f"  ✋ {st['nota']}")
    if st["posizioni"] and not st["ordini"] and not st.get("nota"):
        righe.append("  😴 Nessuna operazione")
    return righe


def messaggio() -> str:
    def stati(gruppo: str) -> dict:
        return {n: json.loads((DIR / gruppo / n / "stato.json").read_text(encoding="utf-8"))
                for n in PORTAFOGLI if (DIR / gruppo / n / "stato.json").exists()}

    avviati = gruppi()
    if not avviati:
        return "📊 Simulazione su carta: non ancora partita."
    primo = stati(avviati[0])
    a, m, g = (int(x) for x in max(st["ultima_data"] for st in primo.values()).split("-"))
    giorno = date(a, m, g)
    righe = [f"📊 Simulazione su carta · {GIORNI[giorno.weekday()]} {giorno:%d/%m/%Y}", f"🚦 Mercato: {verdetto()}",
             "", f"📅 Prima partenza ({date.fromisoformat(avviati[0]):%d/%m/%Y})"]
    for i, (n, st) in enumerate(primo.items()):
        righe += [""] + blocco(i, PORTAFOGLI[n]["etichetta"], st)
    if len(avviati) > 1:
        # una partenza a settimana: per ogni regola la media del guadagno dall'inizio, e dell'ETF negli stessi giorni
        tutti = [stati(g) for g in avviati]
        righe += ["", f"📅 Media delle {len(avviati)} partenze settimanali (guadagno dall'inizio):"]
        for i, n in enumerate(PORTAFOGLI):
            attivi = [s[n] for s in tutti if n in s and s[n]["rif"]]      # solo le partenze che hanno già comprato
            if not attivi:
                continue
            pl = sum(st["valore"] - st["capitale"] for st in attivi) / len(attivi)
            rif = sum(st["rif"]["valore"] - st["capitale"] for st in attivi) / len(attivi)
            righe.append(f"  {NUMERI[i]} {num(pl, 0, True)} € · {NOME_RIF} {num(rif, 0, True)} € · {'🟢' if pl >= rif else '🔴'} {num(pl - rif, 0, True)} €")
    righe += ["", "🧪 Solo simulazione: nessun soldo reale. Gli ordini indicati sono eseguiti alla chiusura della prossima seduta."]
    return "\n".join(righe)


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    avviso = aggiorna() if "--messaggio" not in sys.argv else ""
    testo = (avviso + "\n\n" if avviso else "") + messaggio()
    print(testo)
    invia(testo)
