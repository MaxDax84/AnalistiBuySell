"""Universo ampio: tutte le azioni USA davvero comprabili + grandi e medie europee.

Uso: python studio/universo_ampio.py
USA: screener di nasdaq.com (NYSE, Nasdaq, AMEX), prezzo > 5 $, capitalizzazione > 1 mld $, niente privilegiate/warrant.
Europa: componenti dei principali indici (vedi universo_europa.py; eseguito se manca data/universo_europa.csv).
Scrive data/universo_ampio.csv con la colonna 'mercato'.
"""

import pandas as pd
import requests

from config import DATI
from universo_europa import FILE_UNIVERSO_EUROPA
from universo_europa import main as costruisci_europa

FILE_UNIVERSO_AMPIO = DATI / "universo_ampio.csv"
PREZZO_MINIMO = 5.0
CAP_MINIMA = 1e9
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def screener() -> pd.DataFrame:
    r = requests.get("https://api.nasdaq.com/api/screener/stocks",
                     params={"tableonly": "true", "limit": "10000", "offset": "0"}, headers=H, timeout=60)
    r.raise_for_status()
    t = pd.DataFrame(r.json()["data"]["table"]["rows"])
    t["marketCap"] = pd.to_numeric(t["marketCap"].astype(str).str.replace(",", ""), errors="coerce")
    t["lastsale"] = pd.to_numeric(t["lastsale"].astype(str).str.replace("$", ""), errors="coerce")
    return t


def main() -> None:
    t = screener()
    print(f"screener: {len(t)} righe, {t['marketCap'].notna().sum()} con capitalizzazione")
    t = t[(t["lastsale"] > PREZZO_MINIMO) & (t["marketCap"] > CAP_MINIMA)]
    # '^' = privilegiate, '/' = classi (BRK/B) -> Yahoo usa '-'
    t = t[~t["symbol"].str.contains(r"\^", regex=True)].copy()
    t["Symbol"] = t["symbol"].str.strip().str.replace("/", "-", regex=False)
    t = t.drop_duplicates("Symbol").sort_values("marketCap", ascending=False)
    colonne = ["Symbol", "name", "lastsale", "marketCap"] + [c for c in ("sector", "industry", "country", "ipoyear") if c in t]
    t = t[colonne].rename(columns={"name": "Nome", "lastsale": "prezzo", "marketCap": "market_cap"})
    t["mercato"] = "USA"
    t["indice"] = "USA"
    print(f"USA: {len(t)} titoli (prezzo > {PREZZO_MINIMO:.0f} $, cap > {CAP_MINIMA / 1e9:.0f} mld $)")

    if not FILE_UNIVERSO_EUROPA.exists():
        costruisci_europa()
    eu = pd.read_csv(FILE_UNIVERSO_EUROPA)
    print(f"Europa: {len(eu)} titoli")
    tutti = pd.concat([t, eu], ignore_index=True).drop_duplicates("Symbol")
    DATI.mkdir(parents=True, exist_ok=True)
    tutti.to_csv(FILE_UNIVERSO_AMPIO, index=False)
    print(f"Scritto {FILE_UNIVERSO_AMPIO}: {len(tutti)} titoli")


if __name__ == "__main__":
    main()
