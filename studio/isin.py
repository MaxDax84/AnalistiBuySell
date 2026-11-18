"""Codice ISIN di un titolo, verificato: serve per trovare sul broker esattamente l'azione indicata nel messaggio.

Uso: python studio/isin.py REP.MC ASML.AS DRTS

Yahoo non dà l'ISIN, e la ricerca per nome (Business Insider, quella usata da yfinance) a volte restituisce il
titolo sbagliato: per ASML dà un certificato argentino. Quindi:
  1. si raccolgono i candidati cercando per nome e per ticker;
  2. ogni candidato è verificato al contrario: si chiede a Yahoo "quale titolo ha questo ISIN?" e si accetta solo
     se tra le risposte c'è proprio il nostro ticker.
Un ISIN non verificato NON viene mostrato (meglio nessun codice che un codice sbagliato). I risultati, anche i
"non trovato", sono salvati in data/isin.csv per non richiederli ogni sera.
"""
import re
import sys

import pandas as pd
import requests

from config import DATI

FILE_ISIN = DATI / "isin.csv"
H = {"User-Agent": "Mozilla/5.0"}
RE_ISIN = re.compile(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b")


def candidati(ticker: str, nome: str) -> list[str]:
    """ISIN possibili, dalla ricerca per nome e per ticker (senza suffisso di borsa)."""
    trovati = []
    for q in dict.fromkeys([nome, " ".join(nome.split()[:2]), ticker.split(".")[0].split("-")[0]]):
        if not q:
            continue
        r = requests.get("https://markets.businessinsider.com/ajax/SearchController_Suggest",
                         params={"max_results": 25, "query": q}, headers=H, timeout=15)
        r.raise_for_status()
        trovati += RE_ISIN.findall(r.text)
    return list(dict.fromkeys(trovati))


def ticker_di(isin: str) -> set[str]:
    """I ticker che Yahoo associa a un ISIN."""
    r = requests.get("https://query2.finance.yahoo.com/v1/finance/search", params={"q": isin, "quotesCount": 10, "newsCount": 0},
                     headers=H, timeout=15)
    r.raise_for_status()
    return {q["symbol"] for q in r.json().get("quotes", [])}


def cerca(ticker: str, nome: str) -> str | None:
    """ISIN verificato, "" se nessun candidato corrisponde, None se la ricerca non ha risposto (si riproverà)."""
    try:
        for c in candidati(ticker, nome):
            if ticker in ticker_di(c):
                return c
        return ""
    except Exception:
        return None


def isin_di(tickers: dict[str, str]) -> dict[str, str]:
    """{ticker: nome} -> {ticker: ISIN verificato, o stringa vuota}. Usa e aggiorna data/isin.csv."""
    noti = pd.read_csv(FILE_ISIN, dtype=str).fillna("").set_index("Ticker")["ISIN"].to_dict() if FILE_ISIN.exists() else {}
    nuovi = {t: cerca(t, n) for t, n in tickers.items() if t not in noti}
    nuovi = {t: c for t, c in nuovi.items() if c is not None}
    if nuovi:
        noti.update(nuovi)
        pd.DataFrame({"Ticker": list(noti), "ISIN": list(noti.values())}).sort_values("Ticker").to_csv(FILE_ISIN, index=False)
    return {t: noti.get(t, "") for t in tickers}


if __name__ == "__main__":
    info = pd.read_csv(DATI / "universo_ampio.csv").set_index("Symbol")["Nome"].to_dict()
    for t in sys.argv[1:]:
        nome = str(info.get(t, ""))
        print(t, "|", nome, "|", candidati(t, nome)[:6], "->", cerca(t, nome) or "non verificato")
