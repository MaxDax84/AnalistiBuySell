"""Impostazioni condivise dello studio sull'affidabilità del consenso degli analisti."""

from pathlib import Path

CARTELLA = Path(__file__).resolve().parent
DATI = CARTELLA / "data"
DATI_GIORNALIERI = DATI / "giornaliero"
RISULTATI = CARTELLA / "risultati"

N_TITOLI = 300            # quanti titoli S&P 500 (per capitalizzazione)
ANNI_STORICO = 5          # anni di prezzi e di azioni degli analisti da scaricare
# giorni di borsa dopo il segnale: ogni giorno fino a 15, poi fino a ~12 mesi (250 giorni di borsa)
ORIZZONTI = list(range(1, 16)) + [20, 30, 45, 60, 90, 120, 180, 250]
BENCHMARK = "SPY"         # ETF usato per il rendimento in eccesso
MESI_VALIDITA_GIUDIZIO = 12      # un giudizio più vecchio di così non conta più nel consenso

FILE_UNIVERSO = DATI / "universo.csv"
FILE_PREZZI = DATI / "prezzi.csv"
FILE_AZIONI = DATI / "azioni_analisti.csv"
FILE_FINNHUB = DATI / "consenso_finnhub.csv"


def chiave_finnhub() -> str | None:
    """Chiave Finnhub da variabile d'ambiente o dal secrets.toml dell'app. None se manca o è un segnaposto."""
    import os
    import tomllib

    chiave = os.environ.get("FINNHUB_API_KEY", "").strip()
    if not chiave:
        secrets = CARTELLA.parent / ".streamlit" / "secrets.toml"
        if secrets.exists():
            try:
                chiave = tomllib.load(secrets.open("rb")).get("finnhub", {}).get("api_key", "").strip()
            except Exception:
                chiave = ""
    if not chiave or chiave.upper().startswith("INC"):
        return None
    return chiave


def ticker_yahoo(simbolo: str) -> str:
    """Yahoo usa il trattino per le classi di azioni (BRK.B -> BRK-B)."""
    return simbolo.replace(".", "-")
