# Quanto sono affidabili i giudizi degli analisti?

Universo: 300 titoli S&P 500 per capitalizzazione, prezzi dal 15/10/2021 al 13/11/2026. Segnali analizzati: 10022. Rendimenti sempre IN ECCESSO rispetto alla media dei 300 titoli nello stesso periodo (vedi avvertenze: non SPY), da chiusura del giorno del segnale a chiusura dopo N giorni di borsa. Niente costi di transazione.

## 1. Se seguo un segnale oggi, quando devo uscire?

Per ogni tipo di segnale: l'orizzonte in cui il rendimento medio in eccesso è massimo, e se quel vantaggio è distinguibile dal caso (|t| > 2 ≈ sì).

| segnale | n_segnali | giorno_del_segnale_% | dopo_1gg_% | orizzonte_effetto_max_gg | effetto_max_medio_% | effetto_max_mediano_% | quota_positivi_% | t |
|---|---|---|---|---|---|---|---|---|
| banca: abbassa | 3047 | -1.76 | -0.03 | 1 | -0.03 | 0.02 | 50.18 | -0.61 |
| banca: alza | 3366 | 1.76 | 0.02 | 120 | 0.52 | -3.13 | 43.22 | 0.94 |
| banca: avvia | 3187 | 0.16 | 0.05 | 250 | 12.94 | -7.55 | 39.08 | 3.27 |
| consenso: Compra -> Tieni | 128 | -1.26 | 0.13 | 45 | -1.77 | -2.31 | 38.14 | -1.53 |
| consenso: Tieni -> Compra | 114 | 1.01 | -0.20 | 2 | 0.16 | -0.07 | 46.02 | 0.52 |
| consenso: Tieni -> Vendi | 85 | -1.08 | 0.14 | 5 | -0.19 | -0.39 | 43.53 | -0.32 |
| consenso: Vendi -> Tieni | 88 | 0.89 | -0.01 | 45 | 3.13 | 0.72 | 53.49 | 1.54 |

'giorno_del_segnale' = quanto il titolo si è mosso (oltre la media) nel giorno stesso dell'annuncio: chi compra alla chiusura NON lo prende. Le colonne dopo misurano cosa resta da prendere. Per i segnali negativi (abbassa, -> Vendi, Compra -> Tieni) l'effetto 'giusto' è negativo: il titolo fa peggio della media. Se la media è alta ma la mediana è negativa, pochi titoli esplosi trascinano la media e il titolo tipico ha perso.

## 2. Il consenso del giorno dice qualcosa sul futuro?

Ogni giorno i titoli sono divisi in 5 fasce per punteggio del consenso (solo titoli con almeno 5 banche). Se gli analisti avessero ragione, Q5 dovrebbe battere Q1 in modo crescente con l'orizzonte.

| orizzonte_gg | Q1 peggiori | Q2 | Q3 | Q4 | Q5 migliori | Q5 - Q1 |
|---|---|---|---|---|---|---|
| 1 | 0.01 | -0.01 | -0.01 | 0.01 | -0.01 | -0.02 |
| 2 | 0.03 | -0.02 | -0.02 | 0.02 | -0.01 | -0.04 |
| 3 | 0.04 | -0.03 | -0.03 | 0.04 | -0.02 | -0.06 |
| 4 | 0.06 | -0.03 | -0.05 | 0.05 | -0.03 | -0.09 |
| 5 | 0.07 | -0.04 | -0.06 | 0.06 | -0.04 | -0.11 |
| 6 | 0.09 | -0.05 | -0.07 | 0.07 | -0.05 | -0.14 |
| 7 | 0.11 | -0.05 | -0.08 | 0.07 | -0.06 | -0.16 |
| 8 | 0.12 | -0.06 | -0.09 | 0.09 | -0.07 | -0.19 |
| 9 | 0.14 | -0.07 | -0.10 | 0.10 | -0.08 | -0.21 |
| 10 | 0.16 | -0.07 | -0.11 | 0.11 | -0.09 | -0.24 |
| 11 | 0.17 | -0.08 | -0.12 | 0.12 | -0.09 | -0.27 |
| 12 | 0.19 | -0.09 | -0.13 | 0.13 | -0.10 | -0.29 |
| 13 | 0.21 | -0.10 | -0.14 | 0.14 | -0.11 | -0.31 |
| 14 | 0.22 | -0.11 | -0.16 | 0.14 | -0.11 | -0.33 |
| 15 | 0.24 | -0.12 | -0.17 | 0.15 | -0.12 | -0.36 |
| 20 | 0.34 | -0.19 | -0.20 | 0.17 | -0.13 | -0.48 |
| 30 | 0.49 | -0.30 | -0.28 | 0.20 | -0.13 | -0.62 |
| 45 | 0.67 | -0.43 | -0.39 | 0.23 | -0.09 | -0.76 |
| 60 | 0.83 | -0.58 | -0.45 | 0.23 | -0.04 | -0.88 |
| 90 | 1.18 | -1.19 | -0.54 | 0.37 | 0.17 | -1.01 |
| 120 | 1.36 | -1.82 | -0.89 | 0.85 | 0.44 | -0.92 |
| 180 | 1.07 | -2.29 | -1.50 | 1.07 | 1.34 | 0.27 |
| 250 | 0.91 | -3.33 | -1.95 | 2.60 | 0.70 | -0.20 |

Correlazione (Spearman) giornaliera tra punteggio e rendimento futuro, mediata sui giorni: positiva = gli analisti ordinano bene i titoli; t > 2 ≈ non è caso.

| orizzonte_gg | ic_medio | ic_t | giorni | quota_giorni_ic_positivo_% |
|---|---|---|---|---|
| 1 | 0.01 | 1.88 | 1275.00 | 52.71 |
| 2 | 0.01 | 2.00 | 1274.00 | 52.98 |
| 3 | 0.01 | 1.83 | 1273.00 | 52.16 |
| 4 | 0.00 | 1.40 | 1272.00 | 51.57 |
| 5 | 0.00 | 1.00 | 1271.00 | 51.14 |
| 6 | 0.00 | 0.75 | 1270.00 | 51.50 |
| 7 | 0.00 | 0.56 | 1269.00 | 52.17 |
| 8 | 0.00 | 0.52 | 1268.00 | 51.81 |
| 9 | 0.00 | 0.40 | 1267.00 | 52.09 |
| 10 | 0.00 | 0.21 | 1266.00 | 52.69 |
| 11 | 0.00 | 0.06 | 1265.00 | 50.67 |
| 12 | 0.00 | 0.05 | 1264.00 | 51.11 |
| 13 | 0.00 | 0.07 | 1263.00 | 51.46 |
| 14 | 0.00 | 0.15 | 1262.00 | 51.82 |
| 15 | 0.00 | 0.09 | 1261.00 | 51.63 |
| 20 | -0.00 | -0.39 | 1256.00 | 50.72 |
| 30 | -0.00 | -1.20 | 1246.00 | 50.40 |
| 45 | -0.00 | -1.69 | 1231.00 | 49.63 |
| 60 | -0.01 | -2.85 | 1216.00 | 48.11 |
| 90 | -0.01 | -2.67 | 1186.00 | 44.18 |
| 120 | -0.01 | -1.80 | 1156.00 | 39.79 |
| 180 | -0.00 | -0.17 | 1096.00 | 46.62 |
| 250 | 0.01 | 3.18 | 1026.00 | 46.20 |

Stesso confronto con le etichette fisse (Compra ≥ 4.0, Tieni, Vendi < 3.0):

| orizzonte_gg | Compra | Tieni | Vendi |
|---|---|---|---|
| 1 | -0.01 | -0.00 | 0.06 |
| 2 | -0.02 | -0.00 | 0.13 |
| 3 | -0.02 | -0.01 | 0.19 |
| 4 | -0.03 | -0.01 | 0.26 |
| 5 | -0.03 | -0.01 | 0.32 |
| 6 | -0.03 | -0.01 | 0.39 |
| 7 | -0.04 | -0.02 | 0.46 |
| 8 | -0.04 | -0.02 | 0.52 |
| 9 | -0.05 | -0.02 | 0.59 |
| 10 | -0.06 | -0.02 | 0.66 |
| 11 | -0.07 | -0.03 | 0.73 |
| 12 | -0.08 | -0.03 | 0.80 |
| 13 | -0.09 | -0.03 | 0.87 |
| 14 | -0.10 | -0.03 | 0.94 |
| 15 | -0.11 | -0.03 | 1.00 |
| 20 | -0.17 | -0.04 | 1.32 |
| 30 | -0.21 | -0.07 | 1.95 |
| 45 | -0.32 | -0.10 | 3.03 |
| 60 | -0.47 | -0.15 | 4.53 |
| 90 | -0.84 | -0.24 | 7.41 |
| 120 | -1.07 | -0.33 | 9.78 |
| 180 | -1.75 | -0.54 | 14.20 |
| 250 | -1.38 | -1.05 | 22.35 |

Quanto sono frequenti le etichette (giorni-titolo): Tieni 92%, Compra 5%, Vendi 3%. Gli analisti dicono quasi sempre Compra o Tieni.

## 3. Tabella completa per segnale e orizzonte

| segnale | orizzonte_gg | n | eccesso_medio_% | eccesso_mediano_% | quota_positivi_% | t | p |
|---|---|---|---|---|---|---|---|
| banca: abbassa | 0 | 2848 | -1.76 | -1.23 | 22.61 | -24.53 | 0.00 |
| banca: abbassa | 1 | 3047 | -0.03 | 0.02 | 50.18 | -0.61 | 0.54 |
| banca: abbassa | 2 | 3042 | -0.01 | -0.07 | 48.42 | -0.22 | 0.82 |
| banca: abbassa | 3 | 3039 | -0.02 | -0.01 | 49.72 | -0.31 | 0.75 |
| banca: abbassa | 4 | 3039 | 0.01 | -0.09 | 48.86 | 0.15 | 0.88 |
| banca: abbassa | 5 | 3038 | 0.03 | -0.02 | 49.74 | 0.29 | 0.77 |
| banca: abbassa | 6 | 3035 | 0.13 | -0.11 | 48.76 | 1.32 | 0.19 |
| banca: abbassa | 7 | 3032 | 0.22 | -0.11 | 49.01 | 2.10 | 0.04 |
| banca: abbassa | 8 | 3030 | 0.19 | -0.06 | 49.47 | 1.68 | 0.09 |
| banca: abbassa | 9 | 3027 | 0.25 | -0.06 | 49.45 | 2.14 | 0.03 |
| banca: abbassa | 10 | 3022 | 0.28 | -0.06 | 49.54 | 2.30 | 0.02 |
| banca: abbassa | 11 | 3017 | 0.26 | -0.09 | 49.09 | 2.02 | 0.04 |
| banca: abbassa | 12 | 3014 | 0.20 | -0.11 | 49.10 | 1.49 | 0.14 |
| banca: abbassa | 13 | 3014 | 0.14 | -0.16 | 48.94 | 0.98 | 0.33 |
| banca: abbassa | 14 | 3012 | 0.16 | -0.32 | 47.58 | 1.02 | 0.31 |
| banca: abbassa | 15 | 3011 | 0.15 | -0.26 | 48.06 | 0.92 | 0.36 |
| banca: abbassa | 20 | 3002 | 0.06 | -0.39 | 47.93 | 0.33 | 0.74 |
| banca: abbassa | 30 | 2989 | 0.25 | -0.77 | 46.27 | 1.05 | 0.29 |
| banca: abbassa | 45 | 2967 | 0.40 | -0.93 | 46.58 | 1.41 | 0.16 |
| banca: abbassa | 60 | 2953 | 0.28 | -1.37 | 45.99 | 0.89 | 0.37 |
| banca: abbassa | 90 | 2884 | 0.36 | -1.92 | 45.21 | 0.85 | 0.39 |
| banca: abbassa | 120 | 2822 | 0.61 | -2.98 | 43.76 | 1.07 | 0.28 |
| banca: abbassa | 180 | 2734 | 2.14 | -5.13 | 41.19 | 2.06 | 0.04 |
| banca: abbassa | 250 | 2569 | 1.69 | -8.23 | 39.12 | 1.35 | 0.18 |
| banca: alza | 0 | 3131 | 1.76 | 1.13 | 76.08 | 19.87 | 0.00 |
| banca: alza | 1 | 3366 | 0.02 | -0.06 | 48.40 | 0.46 | 0.64 |
| banca: alza | 2 | 3364 | 0.05 | -0.01 | 49.85 | 0.94 | 0.35 |
| banca: alza | 3 | 3362 | 0.08 | 0.03 | 50.77 | 1.37 | 0.17 |
| banca: alza | 4 | 3362 | 0.07 | -0.06 | 49.29 | 0.99 | 0.32 |
| banca: alza | 5 | 3359 | 0.09 | 0.01 | 50.13 | 1.13 | 0.26 |
| banca: alza | 6 | 3357 | 0.13 | -0.01 | 49.93 | 1.44 | 0.15 |
| banca: alza | 7 | 3357 | 0.19 | -0.05 | 49.54 | 2.09 | 0.04 |
| banca: alza | 8 | 3355 | 0.26 | 0.10 | 51.03 | 2.62 | 0.01 |
| banca: alza | 9 | 3351 | 0.25 | 0.04 | 50.37 | 2.40 | 0.02 |
| banca: alza | 10 | 3342 | 0.29 | 0.01 | 50.12 | 2.57 | 0.01 |
| banca: alza | 11 | 3339 | 0.38 | 0.08 | 50.82 | 3.19 | 0.00 |
| banca: alza | 12 | 3336 | 0.30 | 0.09 | 50.57 | 2.45 | 0.01 |
| banca: alza | 13 | 3333 | 0.29 | -0.06 | 49.59 | 2.28 | 0.02 |
| banca: alza | 14 | 3331 | 0.32 | -0.11 | 49.32 | 2.41 | 0.02 |
| banca: alza | 15 | 3325 | 0.38 | -0.07 | 49.29 | 2.72 | 0.01 |
| banca: alza | 20 | 3311 | 0.38 | -0.14 | 49.38 | 2.38 | 0.02 |
| banca: alza | 30 | 3286 | 0.46 | -0.35 | 48.60 | 2.30 | 0.02 |
| banca: alza | 45 | 3258 | 0.44 | -0.84 | 46.84 | 1.70 | 0.09 |
| banca: alza | 60 | 3228 | 0.28 | -1.27 | 46.19 | 0.90 | 0.37 |
| banca: alza | 90 | 3145 | 0.45 | -2.30 | 44.55 | 1.07 | 0.28 |
| banca: alza | 120 | 3075 | 0.52 | -3.13 | 43.22 | 0.94 | 0.35 |
| banca: alza | 180 | 2931 | 0.51 | -5.71 | 39.68 | 0.62 | 0.53 |
| banca: alza | 250 | 2677 | 0.30 | -8.91 | 37.99 | 0.22 | 0.82 |
| banca: avvia | 0 | 2971 | 0.16 | 0.12 | 53.35 | 4.25 | 0.00 |
| banca: avvia | 1 | 3187 | 0.05 | 0.00 | 50.11 | 1.19 | 0.24 |
| banca: avvia | 2 | 3187 | -0.01 | 0.04 | 50.96 | -0.09 | 0.93 |
| banca: avvia | 3 | 3185 | -0.04 | -0.04 | 49.20 | -0.59 | 0.56 |
| banca: avvia | 4 | 3181 | 0.02 | -0.03 | 49.70 | 0.29 | 0.77 |
| banca: avvia | 5 | 3180 | 0.10 | 0.08 | 50.97 | 1.20 | 0.23 |
| banca: avvia | 6 | 3180 | 0.08 | -0.00 | 49.97 | 0.85 | 0.39 |
| banca: avvia | 7 | 3180 | 0.19 | -0.00 | 49.97 | 1.91 | 0.06 |
| banca: avvia | 8 | 3179 | 0.15 | -0.00 | 49.98 | 1.36 | 0.17 |
| banca: avvia | 9 | 3179 | 0.14 | -0.05 | 49.54 | 1.20 | 0.23 |
| banca: avvia | 10 | 3179 | 0.11 | 0.00 | 50.08 | 0.91 | 0.36 |
| banca: avvia | 11 | 3179 | 0.08 | -0.11 | 48.85 | 0.61 | 0.54 |
| banca: avvia | 12 | 3178 | 0.05 | -0.15 | 48.90 | 0.39 | 0.70 |
| banca: avvia | 13 | 3178 | 0.06 | -0.24 | 48.27 | 0.44 | 0.66 |
| banca: avvia | 14 | 3178 | 0.16 | -0.14 | 48.96 | 1.03 | 0.30 |
| banca: avvia | 15 | 3174 | 0.19 | -0.16 | 48.93 | 1.21 | 0.23 |
| banca: avvia | 20 | 3153 | 0.15 | -0.23 | 48.59 | 0.78 | 0.44 |
| banca: avvia | 30 | 3103 | -0.17 | -0.95 | 45.96 | -0.72 | 0.47 |
| banca: avvia | 45 | 3044 | -0.25 | -1.63 | 44.55 | -0.82 | 0.41 |
| banca: avvia | 60 | 2990 | 0.11 | -1.45 | 45.28 | 0.31 | 0.75 |
| banca: avvia | 90 | 2944 | 0.65 | -2.40 | 44.36 | 1.15 | 0.25 |
| banca: avvia | 120 | 2865 | 1.58 | -3.36 | 42.06 | 2.04 | 0.04 |
| banca: avvia | 180 | 2737 | 5.34 | -5.66 | 41.25 | 3.32 | 0.00 |
| banca: avvia | 250 | 2577 | 12.94 | -7.55 | 39.08 | 3.27 | 0.00 |
| consenso: Compra -> Tieni | 0 | 128 | -1.26 | -0.57 | 35.94 | -3.29 | 0.00 |
| consenso: Compra -> Tieni | 1 | 128 | 0.13 | 0.04 | 52.34 | 0.76 | 0.45 |
| consenso: Compra -> Tieni | 2 | 126 | 0.28 | 0.37 | 55.56 | 1.16 | 0.25 |
| consenso: Compra -> Tieni | 3 | 126 | 0.41 | 0.07 | 51.59 | 1.32 | 0.19 |
| consenso: Compra -> Tieni | 4 | 126 | 0.38 | 0.23 | 51.59 | 1.23 | 0.22 |
| consenso: Compra -> Tieni | 5 | 126 | 0.64 | 0.56 | 56.35 | 2.00 | 0.05 |
| consenso: Compra -> Tieni | 6 | 125 | 0.61 | 0.59 | 53.60 | 1.66 | 0.10 |
| consenso: Compra -> Tieni | 7 | 125 | 0.40 | 0.53 | 54.40 | 0.90 | 0.37 |
| consenso: Compra -> Tieni | 8 | 124 | 0.18 | 0.48 | 53.23 | 0.39 | 0.69 |
| consenso: Compra -> Tieni | 9 | 124 | 0.28 | 0.15 | 52.42 | 0.57 | 0.57 |
| consenso: Compra -> Tieni | 10 | 123 | 0.29 | 0.95 | 60.16 | 0.54 | 0.59 |
| consenso: Compra -> Tieni | 11 | 123 | -0.02 | 0.38 | 53.66 | -0.03 | 0.97 |
| consenso: Compra -> Tieni | 12 | 123 | -0.06 | 0.92 | 57.72 | -0.10 | 0.92 |
| consenso: Compra -> Tieni | 13 | 123 | 0.05 | 0.68 | 56.91 | 0.08 | 0.94 |
| consenso: Compra -> Tieni | 14 | 122 | -0.20 | 0.31 | 50.82 | -0.31 | 0.76 |
| consenso: Compra -> Tieni | 15 | 122 | -0.16 | 0.56 | 54.10 | -0.23 | 0.82 |
| consenso: Compra -> Tieni | 20 | 121 | -0.43 | -0.49 | 46.28 | -0.55 | 0.58 |
| consenso: Compra -> Tieni | 30 | 119 | -1.04 | -1.82 | 42.86 | -1.10 | 0.27 |
| consenso: Compra -> Tieni | 45 | 118 | -1.77 | -2.31 | 38.14 | -1.53 | 0.13 |
| consenso: Compra -> Tieni | 60 | 117 | -1.35 | -2.04 | 42.74 | -0.87 | 0.38 |
| consenso: Compra -> Tieni | 90 | 115 | 0.24 | -2.36 | 40.87 | 0.13 | 0.90 |
| consenso: Compra -> Tieni | 120 | 113 | 0.32 | -4.61 | 44.25 | 0.14 | 0.89 |
| consenso: Compra -> Tieni | 180 | 105 | 2.08 | -2.67 | 40.00 | 0.61 | 0.54 |
| consenso: Compra -> Tieni | 250 | 98 | 0.17 | -4.80 | 42.86 | 0.04 | 0.97 |
| consenso: Tieni -> Compra | 0 | 114 | 1.01 | 0.69 | 64.91 | 4.76 | 0.00 |
| consenso: Tieni -> Compra | 1 | 113 | -0.20 | -0.22 | 45.13 | -1.01 | 0.31 |
| consenso: Tieni -> Compra | 2 | 113 | 0.16 | -0.07 | 46.02 | 0.52 | 0.60 |
| consenso: Tieni -> Compra | 3 | 113 | 0.12 | -0.19 | 47.79 | 0.36 | 0.72 |
| consenso: Tieni -> Compra | 4 | 113 | -0.08 | -0.63 | 41.59 | -0.20 | 0.84 |
| consenso: Tieni -> Compra | 5 | 113 | 0.11 | -0.64 | 46.02 | 0.25 | 0.81 |
| consenso: Tieni -> Compra | 6 | 113 | -0.09 | -0.76 | 37.17 | -0.21 | 0.83 |
| consenso: Tieni -> Compra | 7 | 113 | -0.25 | -1.05 | 44.25 | -0.49 | 0.63 |
| consenso: Tieni -> Compra | 8 | 113 | -0.14 | -0.93 | 40.71 | -0.24 | 0.81 |
| consenso: Tieni -> Compra | 9 | 113 | -0.26 | -0.71 | 43.36 | -0.46 | 0.65 |
| consenso: Tieni -> Compra | 10 | 113 | -0.18 | -0.64 | 45.13 | -0.31 | 0.76 |
| consenso: Tieni -> Compra | 11 | 112 | -0.17 | -1.18 | 46.43 | -0.26 | 0.79 |
| consenso: Tieni -> Compra | 12 | 112 | -0.15 | -0.68 | 42.86 | -0.22 | 0.82 |
| consenso: Tieni -> Compra | 13 | 112 | -0.16 | -0.86 | 43.75 | -0.24 | 0.81 |
| consenso: Tieni -> Compra | 14 | 112 | -0.20 | -0.43 | 45.54 | -0.29 | 0.77 |
| consenso: Tieni -> Compra | 15 | 112 | -0.25 | -0.10 | 48.21 | -0.36 | 0.72 |
| consenso: Tieni -> Compra | 20 | 111 | -1.18 | -1.62 | 38.74 | -1.44 | 0.15 |
| consenso: Tieni -> Compra | 30 | 110 | -1.89 | -1.61 | 35.45 | -1.80 | 0.07 |
| consenso: Tieni -> Compra | 45 | 110 | -0.41 | -0.64 | 48.18 | -0.32 | 0.75 |
| consenso: Tieni -> Compra | 60 | 108 | -1.06 | -1.51 | 44.44 | -0.69 | 0.49 |
| consenso: Tieni -> Compra | 90 | 104 | -1.54 | -1.87 | 43.27 | -0.82 | 0.42 |
| consenso: Tieni -> Compra | 120 | 104 | -2.42 | -5.45 | 38.46 | -1.09 | 0.28 |
| consenso: Tieni -> Compra | 180 | 93 | -4.27 | -8.71 | 35.48 | -1.08 | 0.28 |
| consenso: Tieni -> Compra | 250 | 83 | -4.16 | -13.32 | 36.14 | -0.67 | 0.50 |
| consenso: Tieni -> Vendi | 0 | 85 | -1.08 | -0.96 | 28.24 | -2.04 | 0.04 |
| consenso: Tieni -> Vendi | 1 | 85 | 0.14 | 0.32 | 58.82 | 0.76 | 0.45 |
| consenso: Tieni -> Vendi | 2 | 85 | 0.02 | 0.11 | 50.59 | 0.06 | 0.95 |
| consenso: Tieni -> Vendi | 3 | 85 | -0.09 | 0.37 | 55.29 | -0.23 | 0.82 |
| consenso: Tieni -> Vendi | 4 | 85 | 0.01 | -0.33 | 47.06 | 0.02 | 0.98 |
| consenso: Tieni -> Vendi | 5 | 85 | -0.19 | -0.39 | 43.53 | -0.32 | 0.75 |
| consenso: Tieni -> Vendi | 6 | 85 | 0.25 | 0.03 | 50.59 | 0.40 | 0.69 |
| consenso: Tieni -> Vendi | 7 | 84 | 0.45 | -0.38 | 48.81 | 0.67 | 0.51 |
| consenso: Tieni -> Vendi | 8 | 84 | 0.24 | -0.17 | 50.00 | 0.32 | 0.75 |
| consenso: Tieni -> Vendi | 9 | 84 | 0.31 | -0.16 | 48.81 | 0.44 | 0.66 |
| consenso: Tieni -> Vendi | 10 | 84 | -0.14 | -0.16 | 48.81 | -0.20 | 0.84 |
| consenso: Tieni -> Vendi | 11 | 84 | 0.01 | -0.16 | 47.62 | 0.02 | 0.99 |
| consenso: Tieni -> Vendi | 12 | 83 | 0.19 | -0.29 | 49.40 | 0.25 | 0.80 |
| consenso: Tieni -> Vendi | 13 | 83 | 0.70 | -0.31 | 48.19 | 0.82 | 0.41 |
| consenso: Tieni -> Vendi | 14 | 83 | 1.46 | -0.24 | 46.99 | 1.08 | 0.28 |
| consenso: Tieni -> Vendi | 15 | 83 | 1.35 | 0.35 | 53.01 | 1.16 | 0.25 |
| consenso: Tieni -> Vendi | 20 | 83 | 1.69 | -0.92 | 40.96 | 1.29 | 0.20 |
| consenso: Tieni -> Vendi | 30 | 80 | 3.96 | -1.50 | 45.00 | 1.31 | 0.19 |
| consenso: Tieni -> Vendi | 45 | 80 | 2.56 | -1.91 | 41.25 | 1.01 | 0.32 |
| consenso: Tieni -> Vendi | 60 | 79 | 1.36 | -2.76 | 40.51 | 0.59 | 0.55 |
| consenso: Tieni -> Vendi | 90 | 78 | 0.29 | -2.90 | 47.44 | 0.12 | 0.90 |
| consenso: Tieni -> Vendi | 120 | 77 | 8.11 | -2.38 | 46.75 | 1.14 | 0.26 |
| consenso: Tieni -> Vendi | 180 | 77 | 15.62 | -5.34 | 42.86 | 1.10 | 0.28 |
| consenso: Tieni -> Vendi | 250 | 71 | 19.37 | -8.76 | 39.44 | 1.09 | 0.28 |
| consenso: Vendi -> Tieni | 0 | 88 | 0.89 | 0.70 | 67.05 | 2.70 | 0.01 |
| consenso: Vendi -> Tieni | 1 | 88 | -0.01 | -0.07 | 47.73 | -0.04 | 0.97 |
| consenso: Vendi -> Tieni | 2 | 88 | -0.25 | 0.06 | 51.14 | -0.60 | 0.55 |
| consenso: Vendi -> Tieni | 3 | 88 | 0.08 | -0.15 | 48.86 | 0.19 | 0.85 |
| consenso: Vendi -> Tieni | 4 | 88 | -0.06 | -0.29 | 48.86 | -0.12 | 0.91 |
| consenso: Vendi -> Tieni | 5 | 88 | -0.25 | -0.36 | 45.45 | -0.44 | 0.66 |
| consenso: Vendi -> Tieni | 6 | 88 | -0.62 | -0.36 | 46.59 | -1.04 | 0.30 |
| consenso: Vendi -> Tieni | 7 | 88 | -0.37 | -0.49 | 45.45 | -0.59 | 0.55 |
| consenso: Vendi -> Tieni | 8 | 88 | 0.13 | -0.34 | 47.73 | 0.21 | 0.84 |
| consenso: Vendi -> Tieni | 9 | 88 | 0.14 | -0.21 | 48.86 | 0.20 | 0.85 |
| consenso: Vendi -> Tieni | 10 | 88 | 0.27 | -0.45 | 45.45 | 0.39 | 0.69 |
| consenso: Vendi -> Tieni | 11 | 88 | 0.59 | -0.16 | 46.59 | 0.80 | 0.42 |
| consenso: Vendi -> Tieni | 12 | 88 | 0.54 | -0.25 | 48.86 | 0.66 | 0.51 |
| consenso: Vendi -> Tieni | 13 | 88 | 0.59 | -0.30 | 46.59 | 0.66 | 0.51 |
| consenso: Vendi -> Tieni | 14 | 88 | 0.21 | -0.74 | 42.05 | 0.24 | 0.81 |
| consenso: Vendi -> Tieni | 15 | 88 | 0.79 | -0.96 | 43.18 | 0.82 | 0.41 |
| consenso: Vendi -> Tieni | 20 | 88 | 0.88 | -0.48 | 46.59 | 0.70 | 0.49 |
| consenso: Vendi -> Tieni | 30 | 87 | 1.10 | -0.31 | 49.43 | 0.62 | 0.54 |
| consenso: Vendi -> Tieni | 45 | 86 | 3.13 | 0.72 | 53.49 | 1.54 | 0.13 |
| consenso: Vendi -> Tieni | 60 | 85 | 2.42 | 1.17 | 55.29 | 1.12 | 0.27 |
| consenso: Vendi -> Tieni | 90 | 83 | 3.00 | -1.78 | 39.76 | 1.03 | 0.31 |
| consenso: Vendi -> Tieni | 120 | 83 | 1.91 | -4.20 | 38.55 | 0.60 | 0.55 |
| consenso: Vendi -> Tieni | 180 | 82 | 2.69 | -4.71 | 40.24 | 0.59 | 0.55 |
| consenso: Vendi -> Tieni | 250 | 76 | -4.96 | -10.15 | 31.58 | -1.20 | 0.24 |

## Avvertenze
- Le finestre di orizzonti lunghi si sovrappongono: le t sono ottimistiche, contano soprattutto il segno e l'ordine di grandezza.
- Nessun costo di transazione né tasse.
- L'universo sono i 300 titoli più grandi OGGI: i vincitori degli ultimi anni. Rispetto a SPY battono tutti, anche quelli con 'Vendi', per costruzione. Per questo l'eccesso è calcolato sulla media dell'universo: misura solo se gli analisti separano i migliori dai peggiori.
- Il consenso è ricostruito dalle azioni delle banche riportate da Yahoo; una banca che non aggiorna da 12 mesi esce dal conteggio.
