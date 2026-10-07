# Numeri

Generato da `lavoro/pil-province/calcola.py`. Serie `ISTATP_PIL_PRO_CAPITE` in `app/static/data/nuovi/istat_prov.csv` (riga = numero di riga del file, intestazione = 1). Posti: 1 = valore piu' alto, parita' rotte per nome.

| numero | valore | formula | riga CSV |
|---|---|---|---|
| province con dato | 107 | territori distinti della serie |  |
| anni | 2015-2023 | min e max anno |  |
| 2015 massimo | Milano (Lombardia) 52.900 euro | valore piu' alto | riga 11038 |
| 2015 minimo | Enna (Sicilia) 14.556 euro | valore piu' basso | riga 10813 |
| 2015 rapporto max/min | 3,63 | max / min (non arrotondati) |  |
| 2015 differenza max-min | 38.344 euro | max - min |  |
| 2015 mediana delle 107 | 24.970 euro | mediana dei 107 valori |  |
| 2015 media semplice delle 107 | 25.210 euro | media aritmetica non ponderata |  |
| 2015 prime 5 | Milano 52.900, Bolzano 44.228, Bologna 38.838, Roma 37.239, Aosta 36.465 | ordine decrescente |  |
| 2015 ultime 5 | Sud Sardegna 15.295, Barletta-Andria-Trani 15.124, Caltanissetta 14.968, Agrigento 14.732, Enna 14.556 | ordine crescente da fondo |  |
| 2023 massimo | Milano (Lombardia) 71.274 euro | valore piu' alto | riga 11046 |
| 2023 minimo | Agrigento (Sicilia) 19.007 euro | valore piu' basso | riga 10551 |
| 2023 rapporto max/min | 3,75 | max / min (non arrotondati) |  |
| 2023 differenza max-min | 52.268 euro | max - min |  |
| 2023 mediana delle 107 | 32.456 euro | mediana dei 107 valori |  |
| 2023 media semplice delle 107 | 32.805 euro | media aritmetica non ponderata |  |
| 2023 prime 5 | Milano 71.274, Bolzano 61.545, Bologna 50.088, Modena 48.643, Roma 47.601 | ordine decrescente |  |
| 2023 ultime 5 | Barletta-Andria-Trani 19.836, Sud Sardegna 19.474, Cosenza 19.413, Enna 19.313, Agrigento 19.007 | ordine crescente da fondo |  |
| 2023 prime 10 | Milano, Bolzano, Bologna, Modena, Roma, Parma, Aosta, Trento, Firenze, Reggio Emilia | ordine decrescente |  |
| 2023 ultime 10 | Caserta, Crotone, Caltanissetta, Vibo Valentia, Trapani, Barletta-Andria-Trani, Sud Sardegna, Cosenza, Enna, Agrigento | ordine crescente da fondo |  |
| 2023 ultime 10 regioni | Calabria, Campania, Puglia, Sardegna, Sicilia | regioni delle ultime 10 |  |
| crescita mediana 2015-2023 | 29,7% | mediana di (v2023/v2015 - 1)*100 |  |
| crescita minima | Ferrara 18,4% (25.511 -> 30.212) | min crescita | righe 10831, 10839 |
| crescita massima | Ascoli Piceno 39,7% (23.469 -> 32.788) | max crescita | righe 10588, 10596 |
| province con crescita sotto il 10% | 0 | conteggio g<10 |  |
| province con calo 2015-2023 | 0 | conteggio g<0 |  |
| incremento assoluto mediano | 7.092 euro | mediana di v2023-v2015 |  |
| incremento assoluto massimo | Milano 18.375 euro | max(v2023-v2015) |  |
| incremento assoluto minimo | Cosenza 4.050 euro | min(v2023-v2015) |  |
| prime 5 per crescita % | Ascoli Piceno 39,7%, Bolzano 39,2%, Lecce 37,3%, Matera 37,1%, Rieti 36,8% | ordine decrescente |  |
| ultime 5 per crescita % | Ancona 23,2%, Prato 22,0%, Varese 21,0%, Siena 20,8%, Ferrara 18,4% | ordine |  |
| posti guadagnati (top 5) | Ascoli Piceno +14 (66 -> 52), Cremona +11 (34 -> 23), Arezzo +9 (43 -> 34), Cuneo +9 (28 -> 19), L'Aquila +8 (64 -> 56), Teramo +8 (69 -> 61) | posto2015 - posto2023 |  |
| posti persi (top 5) | Pescara -7 (59 -> 66), Ravenna -8 (22 -> 30), Prato -9 (32 -> 41), Varese -11 (29 -> 40), Ferrara -14 (51 -> 65), Siena -15 (18 -> 33) | posto2015 - posto2023 |  |
| province che nel 2023 stanno nelle prime 10 e c'erano nel 2015 | 10 | intersezione prime 10 |  |
| province che nel 2023 stanno nelle ultime 10 e c'erano nel 2015 | 9 | intersezione ultime 10 |  |
| province che hanno cambiato posto | 96 | conteggio dp!=0 |  |
| scostamento medio assoluto di posto | 3,3 | media di |posto2015-posto2023| |  |
| Milano | 2015: 52.900 (posto 1) 2023: 71.274 (posto 1) | valori e posti | righe 11038, 11046 |
| Roma | 2015: 37.239 (posto 4) 2023: 47.601 (posto 5) | valori e posti | righe 11272, 11280 |
| Napoli | 2015: 18.436 (posto 81) 2023: 24.475 (posto 81) | valori e posti | righe 11065, 11073 |
| Torino | 2015: 29.557 (posto 30) 2023: 39.018 (posto 25) | valori e posti | righe 11380, 11388 |
| Bologna | 2015: 38.838 (posto 3) 2023: 50.088 (posto 3) | valori e posti | righe 10669, 10677 |
| Trieste | 2015: 32.106 (posto 13) 2023: 41.374 (posto 17) | valori e posti | righe 11416, 11424 |
| Crotone | 2015: 16.279 (posto 96) 2023: 20.561 (posto 99) | valori e posti | righe 10795, 10803 |
| 2015 rapporto max/min | 3,63 | Milano / Enna |  |
| 2016 rapporto max/min | 3,72 | Milano / Sud Sardegna |  |
| 2017 rapporto max/min | 3,69 | Milano / Caltanissetta |  |
| 2018 rapporto max/min | 3,78 | Milano / Caltanissetta |  |
| 2019 rapporto max/min | 3,63 | Milano / Caltanissetta |  |
| 2020 rapporto max/min | 3,57 | Milano / Agrigento |  |
| 2021 rapporto max/min | 3,73 | Milano / Enna |  |
| 2022 rapporto max/min | 3,72 | Milano / Sud Sardegna |  |
| 2023 rapporto max/min | 3,75 | Milano / Agrigento |  |
| reddito 04BEC001P: province con dato 2023 | 107 | righe idIndicatore=04BEC001P, Anno=2023, Livello |  |
| nomi del reddito senza corrispondenza | nessuno | confronto nomi |  |
| reddito 2023 massimo | Milano 34.885 euro | max | riga 15560 |
| reddito 2023 minimo | Foggia 14.554 euro | min | riga 15505 |
| reddito 2023 rapporto max/min | 2,40 | max / min |  |
| reddito 2023 Milano | 34.885 euro, posto 1 su 107 | posto per reddito | riga 15560 |
| reddito 2023 Bolzano | 31.352 euro, posto 2 su 107 | posto per reddito | riga 15453 |
| reddito 2023 Agrigento | 14.802 euro, posto 105 su 107 | posto per reddito | riga 15415 |
| reddito 2023 Milano | 34.885 euro, posto 1 su 107 | posto per reddito | riga 15560 |
| reddito 2023 Roma | 25.508 euro, posto 11 su 107 | posto per reddito | riga 15628 |
| PIL/reddito 2023 Milano | 2,04 | PIL per abitante / reddito disponibile pro capite (euro su euro, grandezze diverse: confronto non quota) |  |
| PIL/reddito 2023 Milano | 2,04 | PIL per abitante / reddito disponibile pro capite (euro su euro, grandezze diverse: confronto non quota) |  |
| PIL/reddito 2023 Roma | 1,87 | PIL per abitante / reddito disponibile pro capite (euro su euro, grandezze diverse: confronto non quota) |  |
| PIL/reddito 2023 Agrigento | 1,28 | PIL per abitante / reddito disponibile pro capite (euro su euro, grandezze diverse: confronto non quota) |  |
| correlazione di rango PIL/reddito 2023 | 0,92 | Spearman su 107 province |  |
