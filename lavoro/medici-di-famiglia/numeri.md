# Numeri

Generato da `lavoro/medici-di-famiglia/calcola.py`. Fonte: Istat, Bes, indicatore 12SER027, elaborazione su dati del Ministero della Salute (`app/static/data/Assoluti_BES_Regione.csv`, righe `Livello`; i valori di Italia e ripartizioni da `data/derived/bes_areas_12SER027.csv`, letti dall'appendice statistica Istat). Ripartizioni come `app/data.py` (`REGION_GEO_AREA`), Sud e Isole insieme come Mezzogiorno. Posti dal valore piu alto.

| Affermazione | Formula o riga | Valore |
| --- | --- | --- |
| Serie | righe Livello di 12SER027, venti regioni, ogni anno presente | 2004-2023, 20 anni, nessun buco |
| Italia 2004, 2010, 2019, 2023 (valori Istat, pesati) | data/derived/bes_areas_12SER027.csv riga Italia | 15,8, 25,1, 36,0, 51,7 |
| Nord 2004, 2010, 2019, 2023 (valori Istat, pesati) | data/derived/bes_areas_12SER027.csv riga Nord | 17,6, 33,9, 49,7, 63,8 |
| Centro 2004, 2010, 2019, 2023 (valori Istat, pesati) | data/derived/bes_areas_12SER027.csv riga Centro | 12,5, 19,7, 32,5, 48,7 |
| Mezzogiorno 2004, 2010, 2019, 2023 (valori Istat, pesati) | data/derived/bes_areas_12SER027.csv riga Mezzogiorno | 15,6, 17,8, 22,5, 39,6 |
| Italia oltre la meta per la prima volta | max Italia 2004-2022 contro 2023 | max prima 47,7, 2023 51,7 |
| Rapporto Italia 2023 / 2004 | 51,7 / 15,8 | 3,27 |
| Distanza Nord - Mezzogiorno 2004, 2010, 2019, 2023 | Nord meno Mezzogiorno, valori Istat | 2004: 2,0, 2010: 16,1, 2019: 27,2, 2023: 24,2 |
| Anno di massima distanza | max sulla serie delle distanze | 2019 (27,2) |
| Crescita 2019-2023 per ripartizione (punti) | valore 2023 meno 2019 | Nord 14,1, Centro 16,2, Mezzogiorno 17,1 |
| Media semplice delle venti regioni 2004 e 2023 (non e il dato nazionale) | mean dei venti valori | 14,5, 48,3 |
| Prime tre 2023 | ordinamento per valore | Lombardia 74,0, Veneto 68,7, Valle d'Aosta 61,1 |
| Ultime quattro 2023 | ordinamento per valore | Abruzzo 30,5, Basilicata 29,3, Sicilia 25,5, Molise 21,6 |
| Regioni sopra 50 nel 2023 | conteggio valori > 50 | 11: Lombardia, Veneto, Valle d'Aosta, Sardegna, Trentino Alto Adige, Campania, Emilia-Romagna, Marche, Piemonte, Friuli-Venezia Giulia, Liguria |
| Regioni del Mezzogiorno sopra 50 | intersezione | Campania, Sardegna |
| Posto 2004 e 2023 (da valore piu alto, nessun pari merito) | ordinamento | Trentino Alto Adige 1->5; Campania 2->6; Sardegna 17->4; Liguria 19->11; Sicilia 8->19; Puglia 7->15 |
| Sardegna 2004, 2023, variazione | valore 2023 meno 2004 | 10,0, 60,6, +50,6 |
| Campania 2017, 2019, 2023 | righe serie | 27,0, 34,8, 58,8 |
| Campania variazione 2019-2023 | 58,8 meno 34,8 | 24,0 |
| Variazione 2004-2023, estremi | valore 2023 meno 2004 | Lombardia 21,7->74,0 (+52,3); Veneto 17,8->68,7 (+50,9); Molise 4,6->21,6 (+17,0); Sicilia 13,8->25,5 (+11,7) |
| Maggiori e minori aumenti | ordinamento per variazione | piu alti Lombardia, Veneto, Sardegna; piu bassi Sicilia, Molise |
| Sicilia 2011, 2012, 2013, 2014 (scatto nella serie) | righe serie | 14,7, 21,3, 24,9, 14,2 |
| Abruzzo, Basilicata 2023 | righe serie | 30,5, 29,3 |
