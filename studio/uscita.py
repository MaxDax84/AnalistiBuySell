"""Regole di uscita a confronto sulla classifica momentum (universo ampio).

Uso: python studio/uscita.py        (serve data/prezzi_ampi.parquet da prezzi_ampi.py; 1-2 minuti)

Ingresso: il titolo entra nel 10% migliore della classifica con un segnale nuovo (prima era sotto).
Uscite confrontate:
  classifica          percentile sotto il 40° (regola attuale)
  stop X%             prezzo sceso del X% dal massimo toccato da quando l'hai comprato (trailing stop)
  classifica+stop X%  la prima delle due che scatta
Per ogni regola: statistiche per operazione (mediana, media, % in guadagno, giorni, quanto restituito dal picco,
% di operazioni sotto -30%) e di portafoglio (equipesato sulle posizioni aperte, costi 0,2% a operazione).
Risultato in risultati/uscita_regole.csv.
"""
import numpy as np
import pandas as pd

from classifica import COSTO, fattori, punteggi
from config import RISULTATI
from prezzi_ampi import carica
from universo_ampio import FILE_UNIVERSO_AMPIO, simboli_classifica

SOGLIA_IN, SOGLIA_OUT = 0.9, 0.4
STOP = [0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30]


def simula(regola, stop, P, PC, R, U, univ, date, colonne):
    T, N = P.shape
    in_pos = np.zeros((T, N), dtype=bool)
    ops = []
    for j in range(N):
        p, c = P[:, j], PC[:, j]
        if not np.any(c >= SOGLIA_IN):
            continue
        armato, dentro = True, False
        for t in range(T):
            if np.isnan(p[t]):
                continue
            if not dentro:
                if c[t] >= SOGLIA_IN:
                    if armato:
                        dentro, armato = True, False
                        t0, p0, picco = t, p[t], p[t]
                else:
                    armato = True
                continue
            in_pos[t, j] = True
            picco = max(picco, p[t])
            dd = p[t] / picco - 1
            esci = (regola in ("classifica", "entrambe") and c[t] < SOGLIA_OUT) or \
                   (regola in ("stop", "entrambe") and dd <= -stop)
            if esci or t == T - 1:
                ops.append({"ticker": colonne[j], "entrata": date[t0], "uscita": date[t], "giorni": t - t0,
                            "rend": p[t] / p0 - 1, "max_guadagno": picco / p0 - 1, "dal_picco": dd,
                            "eccesso": (p[t] / p0) / (U[t] / U[t0]) - 1, "aperta": t == T - 1})
                dentro = False
                if c[t] >= SOGLIA_IN:
                    armato = False     # rientra solo con un segnale nuovo
    ops = pd.DataFrame(ops)
    n_pos = in_pos.sum(axis=1)
    rp = np.where(n_pos > 0, np.nansum(np.where(in_pos, R, 0), axis=1) / np.maximum(n_pos, 1), 0.0)
    ent = ops.groupby("entrata").size().reindex(date, fill_value=0).values
    usc = ops[~ops["aperta"]].groupby("uscita").size().reindex(date, fill_value=0).values
    rp_net = rp - COSTO * (ent + usc) / np.maximum(n_pos, 1)
    primo = int(np.argmax(n_pos > 0))
    anni = (T - primo) / 252
    eq = np.cumprod(1 + rp_net[primo:])
    eq_u = np.cumprod(1 + univ[primo:])
    chiuse = ops[~ops["aperta"]]
    return {
        "operazioni": len(ops), "giorni mediana": chiuse["giorni"].median(),
        "rend mediana %": 100 * chiuse["rend"].median(), "rend media %": 100 * chiuse["rend"].mean(),
        "in guadagno %": 100 * (chiuse["rend"] > 0).mean(),
        "max guadagno media %": 100 * chiuse["max_guadagno"].mean(), "dal picco mediana %": 100 * chiuse["dal_picco"].median(),
        "sotto -30% %": 100 * (chiuse["rend"] < -0.3).mean(), "peggiore %": 100 * chiuse["rend"].min(),
        "posizioni medie": n_pos[primo:].mean(),
        "portafoglio annuo netto %": 100 * (eq[-1] ** (1 / anni) - 1), "universo annuo %": 100 * (eq_u[-1] ** (1 / anni) - 1),
        "calo max portafoglio %": 100 * (eq / np.maximum.accumulate(eq) - 1).min(),
        "calo max universo %": 100 * (eq_u / np.maximum.accumulate(eq_u) - 1).min(),
        "anni": anni,
    }


def main():
    close, vol = carica("prezzi_ampi"), carica("volumi_ampi")
    info = pd.read_csv(FILE_UNIVERSO_AMPIO)
    tieni = [c for c in close.columns if c in simboli_classifica(info)]
    close, vol = close[tieni].ffill(limit=3), vol[tieni]
    f = fattori(close, vol, info)
    score, _ = punteggi(f)
    pct = score.rank(axis=1, pct=True)
    r = close.pct_change(fill_method=None)
    univ = r.where(f["ammesso"]).mean(axis=1).fillna(0).values
    U = np.cumprod(1 + univ)
    regole = [("classifica", None)] + [("stop", s) for s in STOP] + [("entrambe", s) for s in (0.12, 0.15, 0.20)]
    righe = []
    for regola, s in regole:
        nome = regola if regola == "classifica" else (f"stop {s:.0%}" if regola == "stop" else f"classifica+stop {s:.0%}")
        print("...", nome, flush=True)
        riga = simula(regola, s, close.values, pct.values, r.values, U, univ, close.index, list(close.columns))
        riga["regola"] = nome
        righe.append(riga)
    tab = pd.DataFrame(righe).set_index("regola")
    RISULTATI.mkdir(parents=True, exist_ok=True)
    tab.to_csv(RISULTATI / "uscita_regole.csv")
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(tab.round(1).T.to_string())


if __name__ == "__main__":
    main()
