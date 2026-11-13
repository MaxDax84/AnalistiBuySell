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

## Simulatore in euro

```
python simula.py AAPL --da 2024-03-01 --giorni 60        # 10.000 € su AAPL quel giorno, venduti 60 gg di borsa dopo
python simula.py AAPL --confronta etichetta --giorni 60  # media di 10.000 € investiti in ogni giorno Compra / Tieni / Vendi
python simula.py --confronta upside --giorni 250         # stesso confronto su tutti i titoli, per fascia di upside
python simula.py --strategie --giorni 20 60 250          # tutte le regole d'ingresso a confronto (salva risultati/strategie.csv)
```

`--confronta` accetta `etichetta`, `upside` (distanza dal prezzo obiettivo), `tendenza` (consenso in salita o
in discesa negli ultimi 20 giorni), `upgrade` (quanti negli ultimi 20 giorni). `--importo` cambia la cifra.

Colonne da guardare, nell'ordine:
- **vs_media_per_titolo_€**: vantaggio rispetto a investire nella media dei 300 titoli, pesando ogni titolo
  allo stesso modo. Se è molto diverso da `vs_media_titoli_€`, la regola vive su pochi titoli esplosi.
- **batte_la_media_%**: quante volte su cento si è fatto meglio della media. Sotto 50 = di solito si perde il
  confronto, e il vantaggio medio viene da pochi colpi grossi.
- **stesso_segno_2_metà**: il vantaggio ha lo stesso segno nel 2021-23 e nel 2024-26? Se "no", non fidarsi.

## Indicatore di regime (quando essere investiti)

```
python regime.py          # scarica 36 anni di S&P 500, VIX, HYG, curva, sussidi, EPU, GPR; valuta; scrive risultati/regime.md
python regime.py --oggi   # solo la lettura di oggi
```

Misura il regime del mercato con 7 condizioni note alla chiusura di ogni giorno e, per ciascuna, cosa ha fatto
l'S&P 500 nei 1-3-6-12 mesi successivi dal 1990, decennio per decennio. Il semaforo conta le condizioni
favorevoli (tendenza, momentum 12 mesi, VIX < 30, credito tranquillo, sussidi vicini ai minimi, EPU non estremo).

Cosa regge su 36 anni (dettagli e tabella completa in `risultati/regime.md`):

| condizione | S&P 500 nei 6 mesi dopo, vs sempre investito | esiti positivi | decenni coerenti |
|---|---|---|---|
| VIX > 30 (panico) | **+8,1%** | 83% | 4/4 |
| 5-10% sotto il massimo di 1 anno | +2,0% | 80% | 3/4 |
| **10-20% sotto il massimo** (il "coltello che cade") | **−4,1%** | 51% | 1/4 |
| oltre 20% sotto il massimo | +2,4% (+4,8% a 12 mesi) | 71% | 1/1 |
| HYG −3/−6% in 60 gg (credito in stress, dal 2007) | **−8,0%** | 44% | 1/2 |
| 12 mesi negativi | −2,7% | 59% | 2/4 |
| EPU alto (incertezza politica tra mediana e top 10%) | −1,6% | 70% | 3/4 |
| EPU estremo (top 10%) | +1,7% | 70% | 3/4 |

Regole di uscita a confronto (1991-2026, liquidità allo 0% quando si è fuori):

| regola | rendimento annuo | peggior calo | peggior anno | anni meglio del sempre investito |
|---|---|---|---|---|
| sempre investito | **9,1%** | −57% | −38% | — |
| solo con 12 mesi positivi | 8,4% | **−25%** | −17% | 12/36 |
| solo sopra la media 200 giorni | 7,0% | −28% | −18% | 5/36 |
| solo con VIX < 30 | 6,3% | −57% | −26% | 7/36 |

Lettura onesta: **nessuna regola di uscita aumenta il rendimento**; le migliori (momentum 12 mesi) lo riducono
di meno di un punto l'anno e dimezzano il calo peggiore. Uscire col VIX alto è la cosa peggiore: si vende sul
fondo. I momenti con il miglior rapporto sono i momenti di panico (VIX > 30, credito in capitolazione, oltre
20% dal massimo), cioè quando è più difficile comprare. La zona pericolosa è quella intermedia: 10-20% sotto
il massimo con il credito in stress.

## File

| file | cosa contiene |
|---|---|
| `config.py` | impostazioni: numero titoli, anni, orizzonti, benchmark |
| `universo.py` | S&P 500 da Wikipedia + capitalizzazione da Yahoo |
| `raccolta.py` | scarica prezzi, azioni degli analisti e split |
| `consenso.py` | scala dei giudizi (1 Strong Sell ... 5 Strong Buy), consenso giornaliero, elenco dei segnali |
| `indicatori.py` | stato giornaliero per titolo: consenso, target (rettificato per gli split), upside, tendenza, upgrade recenti |
| `simula.py` | simulatore in euro e confronto delle regole d'ingresso |
| `regime.py` | indicatore di regime del mercato (36 anni) e lettura di oggi |
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

### Regole d'ingresso a confronto (simula.py --strategie, 10.000 € per ingresso)

| regola | 60 gg: vs media per titolo | batte la media | 250 gg: vs media per titolo | batte la media | stesso segno 2 metà |
|---|---|---|---|---|---|
| consenso = Compra | −187 € | 46% | −1 € | 43% | no |
| Compra + upside < 5% (già oltre il target) | −466 € | 44% | −68 € | 35% | sì a 60 gg |
| consenso = Vendi (46 titoli) | +514 € | 48% | +2.404 € | 36% | sì |
| upside > 30% | +305 € | 48% | +1.782 € | 40% | sì |
| target abbassato > 5% negli ultimi 20 gg | +253 € | 52% | +2.096 € | 46% | sì |
| consenso in discesa (−0,25 in 20 gg) | +264 € | 51% | +1.172 € | 45% | no |

Lettura: seguire "Compra" rende meno di un giorno a caso, e in modo incoerente tra i due periodi. Le uniche
regole che reggono in entrambe le metà sono **contrarie**: comprare dopo che gli analisti hanno tagliato il
target o quando il titolo è crollato molto sotto il target. Ma anche queste battono la media del mercato
meno di una volta su due: il vantaggio viene da una minoranza di recuperi forti. Hanno senso solo spalmate su
molti titoli, mai come scelta del singolo "momento giusto".
