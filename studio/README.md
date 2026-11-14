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

Sentiment dalle opzioni (struttura a termine del VIX dal 2006, SKEW dal 2000, VVIX dal 2007): misurato con lo
stesso metodo, **non aggiunge nulla al livello del VIX**. L'inversione VIX > VIX3M vale +2,1% a 6 mesi, ma
con VIX < 30 diventa −2,8%: tutto il valore sta nei giorni con VIX > 30, già nel semaforo. VVIX > 110 con
VIX < 30: +0,7%. SKEW: decenni discordi. La "compiacenza" (VVIX < 90 e VIX < 15) non è un segnale di
vendita (+0,6%, positivo 83%). Put/call del CBOE e sondaggio AAII non sono scaricabili liberamente. L'order
book (Level 2) non serve a questo orizzonte: informazione che si consuma in minuti, senza storico gratuito.

Lettura onesta: **nessuna regola di uscita aumenta il rendimento**; le migliori (momentum 12 mesi) lo riducono
di meno di un punto l'anno e dimezzano il calo peggiore. Uscire col VIX alto è la cosa peggiore: si vende sul
fondo. I momenti con il miglior rapporto sono i momenti di panico (VIX > 30, credito in capitolazione, oltre
20% dal massimo), cioè quando è più difficile comprare. La zona pericolosa è quella intermedia: 10-20% sotto
il massimo con il credito in stress.

## Verdetto del giorno: STRONG BUY / BUY / WAIT / SMALL SELL

```
python verdetto.py          # valuta le regole dal 1990, simula i piani di liquidità, scrive risultati/verdetto.md
python verdetto.py --oggi   # solo il verdetto di oggi
```

Il verdetto esce da regole fisse (vedi l'intestazione di `verdetto.py`), mai da una lettura delle notizie del
giorno: le notizie sono nei prezzi entro minuti e il "sentiment" misurabile è già dentro VIX, EPU, GPR e HYG.
Ogni sera il workflow lo aggiorna in `risultati/verdetto.md`.

Cosa è successo dal 1990 nei mesi dopo ogni verdetto (S&P 500, vs sempre investito):

| verdetto | quota del tempo | episodi | 6 mesi dopo | 12 mesi dopo | positivi a 6 mesi | decenni coerenti |
|---|---|---|---|---|---|---|
| STRONG BUY | 11% | 94 | **+5,1%** | **+7,0%** | 77% | 4/4 |
| BUY | 13% | 196 | +2,7% | +2,4% | 83% | 4/4 |
| WAIT | 62% | 177 | −0,2% | 0,0% | 77% | 3/4 |
| SMALL SELL | 13% | 129 | **−6,3%** | **−8,5%** | 52% | 2/4 |

E il test che conta per chi ha liquidità da investire, 1.000 € al mese per 36 anni:

| politica | valore finale | moltiplicatore | peggior calo |
|---|---|---|---|
| ogni mese tutto subito | **3,10 M€** | 7,0× | −50% |
| frena su WAIT, accelera su BUY/STRONG BUY, zero su SMALL SELL | 2,65 M€ | 6,0× | −44% |
| tranche normale, zero su SMALL SELL, la cassa accumulata va su BUY/STRONG BUY | 3,07 M€ | 6,9× | −50% |

Conclusione: i verdetti prevedono bene *cosa succede dopo*, ma **aspettarli per investire la liquidità costa più
di quanto renda**, perché WAIT copre il 62% del tempo e il mercato sale anche allora. La liquidità nuova va
investita a scadenze fisse; il verdetto serve a dimensionare l'esposizione del portafoglio esistente (SMALL SELL)
e a non fermarsi, anzi aggiungere, quando scatta STRONG BUY.

## Classifica di tutte le azioni comprabili (universo ampio)

```
python universo_ampio.py     # tutte le azioni USA con prezzo > 5 $ e cap > 300 M$ (screener nasdaq.com) -> ~3.300 titoli
python prezzi_ampi.py        # 5 anni di chiusure e volumi, a blocchi (5-6 minuti) -> data/prezzi_ampi.parquet
python classifica.py         # backtest a 10 fasce + classifica di oggi + confronto col portafoglio -> risultati/classifica.md
python classifica.py --oggi  # solo classifica di oggi (è quello che gira ogni sera su GitHub)
```

Universo: ~2.600 titoli USA (prezzo > 5 $, cap > 1 mld $) + 455 europei (FTSE MIB e Mid Cap, DAX, MDAX, CAC 40,
IBEX 35, AEX, BEL 20, SMI, FTSE 100, OMX Stoccolma 30). Esclusi i titoli poco scambiati (< 2 M$ al giorno) e
quelli con prezzo inchiodato (volatilità < 8% annua = acquisizione in corso: il punteggio li adorava, il rendimento
futuro è zero).

Quattro fattori misurati uno per uno (backtest mensile a 10 fasce, 2022-2026, costi 0,2% per operazione):

| fattore | F10 − F1 annuo | ultimi 12 mesi | mesi con F10 > F1 |
|---|---|---|---|
| **momentum 12-1** | **+6,6%** | +3,6% | 62% |
| inversione 1 mese | −7,3% | +3,2% | 40% |
| bassa volatilità | −26,3% | −19,2% | 42% |
| vicinanza al massimo 52 sett. | −14,3% | −11,0% | 50% |

Il punteggio usa **solo il momentum**, standardizzato dentro ogni mercato (USA / Europa). Gli altri tre escono
col segno rovesciato per **distorsione di sopravvivenza**: l'universo sono i titoli vivi oggi, quindi un titolo
che era volatile tre anni fa ed è ancora quotato sopra il miliardo è quasi per definizione uno che è salito. I
volatili falliti non ci sono. Con dati gratuiti questi fattori non si possono valutare; il momentum ne risente meno
ed è l'unico col segno della letteratura. Fasce del punteggio: F10 (migliori) +10,8% l'anno sopra l'universo,
F1 +2,4% (la U tipica del momentum), F2-F5 sotto. Il 2023 è stato rovesciato (F1 +41%): il momentum perde nei
rimbalzi violenti dopo un crollo, ed è il suo rischio noto.

Portafoglio: un file `studio/portafoglio.csv` con colonne `Ticker,quantita` (non va su GitHub) fa comparire in
`classifica.md` il percentile di ogni tuo titolo e i candidati dal 5% migliore quando un tuo titolo è sotto il 40°.

### Quando uscire: la classifica contro il trailing stop (`uscita.py`)

Domanda: la classifica può dire di comprare *prima* del +200% e di vendere *prima* del −60%? No: il momentum
misura il passato. Quando un titolo entra nel 10% migliore ha già fatto +58% (mediana) nei 12 mesi; quando scende
sotto il 40° percentile ha già restituito il 20% dal picco. Allora si è provato a uscire con uno stop sul prezzo
(vendi quando scende del X% dal massimo toccato da quando l'hai comprato), 2022-2026, 2.900-7.300 operazioni:

| uscita | operazioni | giorni | mediana | media | in guadagno | sotto −30% | portafoglio annuo netto |
|---|---|---|---|---|---|---|---|
| **classifica (sotto il 40°)** | 2.842 | 185 | +1,5% | **+18,9%** | 52% | 7,7% | **+26,4%** |
| stop 8% | 7.279 | 17 | −3,1% | +1,8% | 39% | 0,2% | +15,0% |
| stop 12% | 5.890 | 30 | −4,1% | +3,7% | 40% | 0,4% | +17,5% |
| stop 20% | 4.187 | 67 | −6,0% | +9,4% | 41% | 1,0% | +19,3% |
| stop 30% | 3.104 | 132 | −10,1% | +14,3% | 39% | 11,5% | +20,0% |
| classifica + stop 15% | 5.246 | 38 | −3,5% | +5,1% | 42% | 0,4% | +19,2% |

(universo equipesato: +22,8% l'anno nello stesso periodo, gonfiato dalla sopravvivenza; calo massimo −18,5% per
tutti, lo stop non lo riduce.) Lo stop fa esattamente quello che promette, elimina le operazioni sotto −30%, ma
costa 6-11 punti l'anno: vende sul rumore (con lo stop al 12% l'operazione tipica dura 30 giorni) e taglia proprio
i titoli che poi fanno il +100%. Più lo stop è largo, più ci si avvicina alla regola della classifica, che resta la
migliore. Conclusione: le perdite del singolo titolo si gestiscono con il numero di titoli (20-30, mai uno solo)
e con l'esposizione di portafoglio decisa dal semaforo, non con lo stop sul singolo titolo.

## Il piano da 2.000 € (`piano.py`) e la simulazione su carta (`carta.py`)

`piano.py` prova la regola operativa: 2.000 € su K titoli del 10% migliore della classifica, vendita sotto il 40°
percentile, costi (2 € + 0,2% a ordine) e imposta del 26% inclusi, 39 date di partenza, 12 mesi ciascuna.
Con 5 titoli e filtro "prudente" (volatilità annua <= 50%) il valore finale mediano è ~2.700-2.800 € contro 2.275 €
di SPY, e la frequenza del controllo non conta: ogni sera, ogni settimana e ogni mese danno lo stesso risultato
e lo stesso numero di ordini (~15 l'anno), con o senza conferma di 5-10 sere sotto soglia.
Per anno di partenza il vantaggio sta quasi tutto nel 2023-2024; nel 2022 e nel 2025 è circa pari all'indice.

Limiti che gonfiano questi numeri: l'universo è fatto dei titoli che OGGI valgono più di 1 mld $ (chi è salito è
dentro, chi è sceso è fuori), sono 4 anni di un solo tipo di mercato, e le soglie sono scelte sugli stessi dati.
Per questo esiste `carta.py`: applica la stessa regola dal vivo, senza soldi, ogni sera nel workflow, salva lo
stato in `carta/` e manda un messaggio Telegram con valore, P&L del giorno e totale, confronto con SPY e ordini
per la seduta successiva. È l'unica verifica senza quei difetti; servono mesi prima di poterla leggere.

### Le idee per migliorare la regola, messe alla prova (`modelli.py`, `piano.py --modelli`, `piano.py --rumore`)

Stesse 39 partenze, 5 titoli, controllo ogni sera, costi e tasse inclusi (SPY: 2.275 € mediani):

| modello | finale mediano | peggiore | batte SPY | calo peggiore mediano |
|---|---|---|---|---|
| base (regola di partenza) | 2.774 € | 1.890 € | 82% | −20% |
| senza pari merito in cima alla classifica | 2.581 € | 1.778 € | 82% | −21% |
| universo scelto con gli scambi di quel giorno | 2.693 € | 1.673 € | 90% | −19% |
| + momentum "pulito" (salita regolare) | 2.436 € | 1.878 € | 72% | **−13%** |
| + niente titoli gemelli (correlazione < 0,5) | 2.579 € | 1.952 € | 82% | −18% |
| + freno di mercato (niente acquisti con SMALL SELL) | 2.705 € | 1.673 € | 90% | −19% |
| tutto insieme | 2.452 € | **1.936 €** | 79% | **−13%** |
| 5 titoli pescati A CASO tra i candidati (20 prove) | 2.290 € (2.196-2.398) | 1.700 € | 49% | |

Cosa dicono:
- **Nessuna idea aumenta il rendimento del backtest.** Il momentum pulito e "tutto insieme" rendono meno ma
  dimezzano quasi il calo peggiore: scambiano guadagno con tranquillità.
- **L'universo corretto non fa crollare il risultato** (2.693 contro 2.581 € a parità di segnale): il difetto della
  capitalizzazione di oggi pesa meno del temuto. Restano fuori i titoli spariti dal listino, che non si possono recuperare.
- **Stare nel 10% migliore non basta.** Pescando a caso tra i candidati si ottiene l'indice (49% di vittorie su SPY).
  Tutto il vantaggio sta nei primissimi della classifica: è lì che conta l'ordine, ed è lì che il rischio di aver
  misurato fortuna (pochi titoli estremi, sopravvissuti) è più alto.
- Il freno di mercato e il filtro sui gemelli spostano poco: nel periodo c'è un solo episodio di mercato negativo.
- Le revisioni degli utili attesi (`revisioni.py`) non hanno storico gratuito: si raccolgono ogni sera per i primi
  60 candidati in `data/revisioni/` e si provano solo su carta.

Su carta corrono tre portafogli da 2.000 € (`carta/base`, `carta/prudente`, `carta/utili`): la regola di partenza,
"tutto insieme", e "tutto insieme" comprando solo titoli con utili attesi rivisti al rialzo negli ultimi 30 giorni.

### Come si giudica la simulazione (criteri fissati il 14/11/2026, prima di vedere i risultati)

Ogni settimana parte un nuovo gruppo dei tre portafogli (`carta/AAAA-MM-GG/`), fino a 52 partenze. Partenze vicine
comprano quasi gli stessi titoli: 26 partenze in sei mesi valgono come 6-8 prove indipendenti, non 26.
1. Nessuna decisione prima di 6 mesi.
2. Una regola passa se, sulla media delle sue partenze, non perde più di 5 punti rispetto a SPY, non ha cali
   peggiori del 25% e fa un numero di ordini vicino al backtest (~15 l'anno).
3. Se ne passano più di una si sceglie quella con i cali minori, non quella che ha reso di più.
4. Se non ne passa nessuna, l'alternativa è un ETF sull'indice.
Con soldi veri si parte comunque da 2.000 €, tenendo la simulazione accesa accanto.

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
| `verdetto.py` | verdetto a 4 livelli da regole fisse, verifica storica, piani di liquidità |
| `universo_ampio.py`, `prezzi_ampi.py` | tutte le azioni USA comprabili e i loro prezzi |
| `classifica.py` | punteggio a 4 fattori, backtest a 10 fasce, classifica di oggi, confronto col portafoglio |
| `uscita.py` | regole di uscita a confronto: classifica contro trailing stop (risultato: lo stop costa rendimento) |
| `piano.py` | backtest del piano 2.000 € su K titoli con rotazione sulla classifica (costi, tasse 26%, partenze multiple) |
| `modelli.py` | varianti della regola: universo alla data, graduatoria senza pari merito, momentum pulito, titoli gemelli, freno di mercato |
| `revisioni.py` | revisioni degli utili attesi (fotografia serale dei candidati) |
| `carta.py`, `telegram.py` | simulazione su carta della regola (stato in `carta/`) e invio del messaggio serale su Telegram |
| `pagina.py` | genera la pagina web `docs/index.html` |
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
