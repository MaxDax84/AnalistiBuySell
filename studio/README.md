# Studio: quanto sono affidabili i giudizi degli analisti?

Domanda: se oggi seguo un "Compra" / "Vendi" degli analisti, guadagno? E dopo quanti giorni devo uscire?

Universo: i 300 titoli dell'S&P 500 più grandi per capitalizzazione. Dati: prezzi e azioni delle singole
banche (upgrade, downgrade, avvio di copertura) da Yahoo Finance, 5 anni. Il consenso di ogni giorno è
ricostruito dalle azioni delle banche ("point-in-time": solo ciò che era noto quel giorno).

Le risposte sono in `risultati/riepilogo.md` (tabelle) e `risultati/grafici.html` (curve interattive).

## Come si usa

```
cd studio
python universo.py      # lista dei 300 titoli -> data/universo.csv (una volta, o per aggiornarla)
python raccolta.py      # prezzi + azioni degli analisti -> data/  (qualche minuto)
python analisi.py       # calcola tutto -> risultati/
python giornaliero.py   # fotografia del consenso di oggi -> data/giornaliero/AAAA-MM-GG.csv
```

Il file `.github/workflows/raccolta-giornaliera.yml` esegue `giornaliero.py` ogni sera di borsa su
GitHub Actions e salva il risultato nel repository. Dopo un paio di mesi quei file permettono di
rifare l'analisi con dati raccolti "dal vivo", senza il rischio che lo storico sia stato corretto.

Finnhub è facoltativo: se c'è la chiave (variabile `FINNHUB_API_KEY`, o `.streamlit/secrets.toml`,
o il Secret del repository su GitHub) viene salvato anche il suo consenso mensile.

## File

| file | cosa contiene |
|---|---|
| `config.py` | impostazioni: numero titoli, anni, orizzonti, benchmark |
| `universo.py` | S&P 500 da Wikipedia + capitalizzazione da Yahoo |
| `raccolta.py` | scarica prezzi e azioni degli analisti |
| `consenso.py` | scala dei giudizi (1 Strong Sell ... 5 Strong Buy), consenso giornaliero, elenco dei segnali |
| `analisi.py` | rendimenti in eccesso, studio degli eventi, fasce di consenso, riepilogo |
| `giornaliero.py` | fotografia del giorno (per la raccolta automatica) |
| `data/` | dati scaricati (`universo.csv` serve anche alla raccolta automatica) |
| `risultati/` | tabelle e grafici |

## Come leggere i numeri

- Tutti i rendimenti sono **in eccesso rispetto alla media dei 300 titoli** nello stesso periodo. Non
  rispetto a SPY: l'universo sono i vincitori degli ultimi anni e batterebbero SPY per costruzione,
  anche i "Vendi". Così resta solo la domanda utile: gli analisti separano i migliori dai peggiori?
- "Giorno del segnale" = movimento dalla chiusura precedente alla chiusura del giorno dell'annuncio.
  Chi agisce a fine giornata non lo prende.
- Le finestre lunghe si sovrappongono, quindi le `t` sono ottimistiche: contano segno e ordine di grandezza.
- Se la media è positiva ma la mediana è negativa, pochi titoli esplosi trascinano la media.

## Cosa è emerso (13 novembre 2026, 10.022 segnali)

1. **Il mercato reagisce nel giorno stesso dell'annuncio**: un upgrade vale in media +1,8% oltre la
   media quel giorno, un downgrade −1,8%. Il giorno dopo non resta nulla: +0,02% e −0,03%.
2. **Dopo il segnale non c'è un orizzonte di uscita che funzioni.** Né a 1 giorno né a 15 né a 12 mesi
   l'eccesso medio dopo un upgrade o un downgrade è distinguibile dal caso, e la mediana a lunga
   scadenza è negativa per tutti i tipi di segnale.
3. **Il consenso del giorno non ordina i titoli.** La correlazione tra punteggio e rendimento futuro è
   praticamente zero fino a 15 giorni, leggermente negativa a 2-4 mesi (i titoli peggio giudicati
   fanno un po' meglio), leggermente positiva a 12 mesi. Troppo piccola e instabile per usarla.
4. Gli avvii di copertura mostrano una media alta a 12 mesi (+13%) ma solo 39% di casi positivi e
   mediana −7,6%: sono pochi titoli diventati enormi, non un segnale ripetibile.
