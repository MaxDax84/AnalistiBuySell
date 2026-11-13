"""Universo europeo: grandi e medie capitalizzazioni dei principali indici, con i ticker di Yahoo.

Uso: python studio/universo_europa.py
Fonte: tabelle dei componenti su Wikipedia. Scrive data/universo_europa.csv (Symbol, Nome, mercato, indice).
"""

import io

import pandas as pd
import requests

from config import DATI

FILE_UNIVERSO_EUROPA = DATI / "universo_europa.csv"
H = {"User-Agent": "Mozilla/5.0"}

# indice: (url, suffisso da aggiungere se il ticker non ce l'ha già, mercato)
INDICI = {
    "FTSE MIB": ("https://en.wikipedia.org/wiki/FTSE_MIB", ".MI", "Italia"),
    "FTSE Italia Mid Cap": ("https://it.wikipedia.org/wiki/FTSE_Italia_Mid_Cap", ".MI", "Italia"),
    "DAX": ("https://en.wikipedia.org/wiki/DAX", ".DE", "Germania"),
    "MDAX": ("https://en.wikipedia.org/wiki/MDAX", ".DE", "Germania"),
    "CAC 40": ("https://en.wikipedia.org/wiki/CAC_40", ".PA", "Francia"),
    "IBEX 35": ("https://en.wikipedia.org/wiki/IBEX_35", ".MC", "Spagna"),
    "AEX": ("https://en.wikipedia.org/wiki/AEX_index", ".AS", "Paesi Bassi"),
    "BEL 20": ("https://en.wikipedia.org/wiki/BEL_20", ".BR", "Belgio"),
    "SMI": ("https://en.wikipedia.org/wiki/Swiss_Market_Index", ".SW", "Svizzera"),
    "FTSE 100": ("https://en.wikipedia.org/wiki/FTSE_100_Index", ".L", "Regno Unito"),
    "OMX Stockholm 30": ("https://en.wikipedia.org/wiki/OMX_Stockholm_30", ".ST", "Svezia"),
}
SUFFISSI = (".MI", ".DE", ".PA", ".MC", ".AS", ".BR", ".SW", ".L", ".ST", ".F", ".VI", ".CO", ".HE", ".OL", ".LS", ".IR")


def tabella_componenti(url: str) -> pd.DataFrame | None:
    tabs = pd.read_html(io.StringIO(requests.get(url, headers=H, timeout=30).text))
    for t in tabs:
        cols = [str(c) for c in t.columns]
        if len(t) >= 15 and any(k in c for c in cols for k in ("icker", "Symbol", "Codice")):
            return t
    return None


def ticker_yahoo(grezzo: str, suffisso: str) -> str | None:
    s = str(grezzo).split(":")[-1].replace("\xa0", "").strip().upper()
    if not s or s == "NAN" or len(s) > 12:
        return None
    if s.endswith(SUFFISSI):
        return s
    s = s.replace(".", "-")          # BT.A -> BT-A, classi di azioni
    return s + suffisso


def main() -> None:
    righe = []
    for indice, (url, suffisso, mercato) in INDICI.items():
        t = tabella_componenti(url)
        if t is None:
            print(f"  {indice}: tabella non trovata, salto")
            continue
        col_t = next(c for c in t.columns if any(k in str(c) for k in ("icker", "Symbol", "Codice")))
        col_n = next((c for c in t.columns if any(k in str(c) for k in ("Company", "Società", "Name", "Azienda", "Constituent"))), None)
        n = 0
        for _, r in t.iterrows():
            y = ticker_yahoo(r[col_t], suffisso)
            if y:
                righe.append({"Symbol": y, "Nome": str(r[col_n])[:60] if col_n is not None else "", "mercato": mercato, "indice": indice})
                n += 1
        print(f"  {indice}: {n} titoli")
    tab = pd.DataFrame(righe).drop_duplicates("Symbol")
    DATI.mkdir(parents=True, exist_ok=True)
    tab.to_csv(FILE_UNIVERSO_EUROPA, index=False)
    print(f"Scritto {FILE_UNIVERSO_EUROPA}: {len(tab)} titoli europei")


if __name__ == "__main__":
    main()
