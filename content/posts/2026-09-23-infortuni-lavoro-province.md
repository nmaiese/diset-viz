---
title: 'Infortuni gravi sul lavoro: i grandi settori non bastano a spiegare la mappa'
seo_title: 'Infortuni gravi sul lavoro: perché Arezzo non è Mantova'
slug: infortuni-lavoro-province
description: Arezzo e Mantova hanno la stessa quota di lavoro in campi, fabbriche e cantieri, ma ad Arezzo gli infortuni gravi sono più di tre volte. Abbiamo cercato perché.
date: 2026-09-23
author: Redazione Divario Italia
cover: /static/img/blog/infortuni-lavoro-province.jpg
cover_alt: Un cartello bianco con la scritta Caduta materiali dall'alto, legato a una rete arancione da cantiere.
cover_caption: Un cartello di cantiere a Pontebba, in Friuli-Venezia Giulia.
cover_credit:
  author: Herzi Pinki
  license: CC BY-SA 4.0
  license_url: https://creativecommons.org/licenses/by-sa/4.0
  source_url: https://commons.wikimedia.org/wiki/File:Caduta_materiali_dall%27_alto,_San_Rocco_03.jpg
  source_name: Wikimedia Commons
  changes: Ritagliata e ridimensionata
tags:
- Lavoro
- Sicurezza sul lavoro
- Province
indicator: bes-03LAV007
indicator_label: Tasso di infortuni sul lavoro mortali e con inabilità permanente
trend:
  topic: sicurezza-lavoro
  detected: 2026-09-23
  ranking: data/trend/2026-09-23/ranking.json
  score:
    interest: 0.95
    data: 0.68
    story: 0.89
    total: 0.746
    rank: 7
  signals:
  - type: google_news_principali
    text: Tragedia al Colosseo, Andrea Moretti morto a 22 anni mentre installava il nuovo impianto di illuminazione (RomaToday)
    source: Google News Italia, notizie principali
    url: https://news.google.com/rss/articles/CBMidkFVX3lxTE1WNmhmVG9RdXY5c1lzelp6blhMWWZPMDdUWm1jQUxYTWh5cHpFWS1XZ0FmWkFZNFdvVEVPejR4SzJTc3pWSXp5VVFrVFJrSm1RWG5Bb2lGTG5QSTRNY0JIREVNTTFyOXhCQUc5SEw1QWw2d3lycFE?oc=5
    date: 2026-09-23
  - type: google_news_tema
    text: 56 titoli sulle morti e gli infortuni sul lavoro negli ultimi sette giorni, fra cui Sant'Arcangelo (Potenza) e Polesine Parmense
    source: Google News Italia, ricerca degli ultimi 7 giorni
    url: https://news.google.com/rss/search?q=(morto%20sul%20lavoro%20OR%20incidente%20sul%20lavoro%20OR%20infortuni)%20when:7d&hl=it&gl=IT&ceid=IT:it
    date: 2026-09-23
  - type: google_trends_interesse
    text: 'morti sul lavoro: interesse degli ultimi 7 giorni 11,49 volte la media degli 83 precedenti. Regioni con piu'' interesse: Lombardia, Emilia-Romagna, Toscana'
    source: Google Trends (pytrends), Italia, finestra today 3-m e now 7-d
    url: https://trends.google.com/trends/explore?geo=IT&q=morti%20sul%20lavoro
    date: 2026-09-23
  - type: google_trends_interesse
    text: 'incidente sul lavoro: interesse degli ultimi 7 giorni 2,45 volte la media degli 83 precedenti. Regioni con piu'' interesse: Basilicata, Emilia-Romagna, Lombardia'
    source: Google Trends (pytrends), Italia, finestra today 3-m e now 7-d
    url: https://trends.google.com/trends/explore?geo=IT&q=incidente%20sul%20lavoro
    date: 2026-09-23
dataset:
  name: Infortuni sul lavoro mortali e con inabilità permanente e composizione settoriale dell'occupazione, per provincia
  description: Infortuni sul lavoro mortali e con inabilità permanente ogni 10.000 occupati per provincia, regione e ripartizione (2018-2022), quota di occupati in agricoltura, industria e costruzioni per provincia (2022) e tasso atteso in base ai soli settori.
  method: 'Tassi: dati Istat su fonte Inail, senza rielaborazione, compresi i valori ufficiali per ripartizione. Tasso atteso: regressione lineare del tasso provinciale 2022 sulle quote di occupati in agricoltura, industria in senso stretto e costruzioni (Istat, Conti territoriali), elaborazione Divario Italia con lo script scripts/articoli_trend/elab_settori_infortuni.py.'
  temporal: 2018/2022
  spatial: Italia, ripartizioni, regioni e province
  creator: Istat, Inail
  source_url: https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip
  download: /static/data/articles/infortuni-lavoro-province.csv
external_figures:
- value: 14,8
  what: tasso di infortuni gravi degli uomini, 2022
  source: Istat, Il benessere equo e sostenibile in Italia, Rapporto Bes 2025
  url: https://www.istat.it/wp-content/uploads/2025/11/Bes-2024-Ebook.pdf
- value: 5,8
  what: tasso di infortuni gravi delle donne, 2022
  source: Istat, Il benessere equo e sostenibile in Italia, Rapporto Bes 2025
  url: https://www.istat.it/wp-content/uploads/2025/11/Bes-2024-Ebook.pdf
- value: 24,1
  what: tasso di infortuni gravi degli uomini stranieri, 2022
  source: Istat, Il benessere equo e sostenibile in Italia, Rapporto Bes 2025
  url: https://www.istat.it/wp-content/uploads/2025/11/Bes-2024-Ebook.pdf
- value: 13,7
  what: tasso di infortuni gravi degli uomini italiani, 2022
  source: Istat, Il benessere equo e sostenibile in Italia, Rapporto Bes 2025
  url: https://www.istat.it/wp-content/uploads/2025/11/Bes-2024-Ebook.pdf
- value: 26,0
  what: tasso di infortuni gravi fra 65 e 89 anni, 2022
  source: Istat, Il benessere equo e sostenibile in Italia, Rapporto Bes 2025
  url: https://www.istat.it/wp-content/uploads/2025/11/Bes-2024-Ebook.pdf
- value: '67'
  what: denunce mortali nelle costruzioni, gennaio-luglio 2025
  source: Inail, comunicato dell'8 settembre 2026
  url: https://www.inail.it/portale/it/inail-comunica/comunicati-stampa/comunicato-stampa.2026.09.denunce-di-infortuni-e-malattie-professionali-i-dati-inail-di-luglio.html
- value: '76'
  what: denunce mortali nelle costruzioni, gennaio-luglio 2026
  source: Inail, comunicato dell'8 settembre 2026
  url: https://www.inail.it/portale/it/inail-comunica/comunicati-stampa/comunicato-stampa.2026.09.denunce-di-infortuni-e-malattie-professionali-i-dati-inail-di-luglio.html
- value: 15,8
  what: tasso di infortuni gravi fra 50 e 64 anni, 2022
  source: Istat, Il benessere equo e sostenibile in Italia, Rapporto Bes 2025
  url: https://www.istat.it/wp-content/uploads/2025/11/Bes-2024-Ebook.pdf
- value: '422'
  what: denunce mortali in occasione di lavoro, esclusi studenti e tragitti, gennaio-luglio 2026
  source: Inail, comunicato dell'8 settembre 2026
  url: https://www.inail.it/portale/it/inail-comunica/comunicati-stampa/comunicato-stampa.2026.09.denunce-di-infortuni-e-malattie-professionali-i-dati-inail-di-luglio.html
- value: '432'
  what: denunce mortali in occasione di lavoro, esclusi studenti e tragitti, gennaio-luglio 2025
  source: Inail, comunicato dell'8 settembre 2026
  url: https://www.inail.it/portale/it/inail-comunica/comunicati-stampa/comunicato-stampa.2026.09.denunce-di-infortuni-e-malattie-professionali-i-dati-inail-di-luglio.html
---

Andrea Moretti aveva 22 anni ed è morto nella notte dentro il Colosseo, mentre lavorava al nuovo impianto di illuminazione. La notizia è arrivata il 23 settembre. Nei giorni precedenti erano morti un operaio nel Parmense e uno nel Potentino. La domanda è sempre la stessa: dove si rischia di più, e perché?

La risposta che sembra ovvia è: dove si lavora di più nei campi, nelle fabbriche e nei cantieri. Abbiamo verificato provincia per provincia, con i grandi settori dell'Istat. Spiegano poco.

Arezzo e Mantova hanno quasi la stessa quota di occupati in agricoltura, industria e costruzioni, il **39,6% e il 38,9%**. Ad Arezzo gli infortuni mortali o invalidanti sono 20,3 ogni 10.000 occupati, a Mantova 5,8.
{: .data-callout}

## In breve

- Nel 2022 in Italia ci sono stati 11,0 infortuni sul lavoro mortali o con invalidità permanente ogni 10.000 occupati. Nel Mezzogiorno 13,0, al Centro 11,9, al Nord 9,6.
- Le province più colpite sono in Toscana, Umbria, Abruzzo e Basilicata. Le meno colpite sono quasi tutte nel Nord-Ovest.
- Agricoltura, industria e costruzioni, prese come grandi settori, spiegano poco più di un decimo delle differenze fra province.

## Che cosa conta questo indicatore

Non conta solo i morti. Conta gli infortuni che hanno ucciso qualcuno o gli hanno lasciato un danno permanente, divisi per il numero degli occupati. Il dato è dell'Istat su fonte Inail e arriva al 2022. Una nota dell'Istat avverte che i dati di quell'anno sono provvisori.

## Una mappa che passa per il centro Italia

In cima ci sono Arezzo con 20,3, Potenza con 20,1 e Massa-Carrara con 19,8, poi Teramo, Grosseto, Perugia, Lucca, Chieti e Siena. In fondo non ci sono soltanto le grandi città. C'è quasi tutto il Nord-Ovest: Verbano-Cusio-Ossola 4,7, Novara 4,8, Mantova 5,8, Pavia 5,9, Biella 6,3, Milano 6,4, Torino 6,6.

<!-- figura: province-2022 -->

## I settori non bastano

Abbiamo preso dall'Istat la quota di occupati in agricoltura, industria e costruzioni di ogni provincia, e calcolato quale tasso di infortuni avrebbe ciascuna se contassero solo quelle quote. Il metodo è una regressione lineare sulle 103 province per cui l'Istat pubblica il dato. Ne esce che i tre settori spiegano poco più di un decimo delle differenze. A parità di punti di quota, l'edilizia è quello che pesa di più.

<!-- figura: settori-infortuni -->

Le province in cima restano lontanissime da quello che i settori farebbero prevedere. Arezzo, in base ai settori, dovrebbe avere 12,3 infortuni gravi ogni 10.000 occupati, e ne ha 20,3. Massa-Carrara 12,1 e ne ha 19,8. Perugia 11,8 e ne ha 18,3. Potenza 13,7 e ne ha 20,1. Dall'altra parte Mantova dovrebbe avere 11,7 e ne ha 5,8, Pavia 11,6 e ne ha 5,9, il Verbano-Cusio-Ossola 12,0 e ne ha 4,7.

Questo non vuol dire che il tipo di lavoro non conti. I tre settori dell'Istat sono larghi: dentro l'industria ci sono le cave di marmo e gli uffici delle aziende. La Consulta interassociativa italiana per la prevenzione, che lavora sugli open data Inail, scrive che è corretto confrontare i tassi solo dentro un comparto omogeneo. È il passo successivo, e servono i dati per comparto. Che cosa pesi nel resto, oggi i dati pubblici non lo dicono. Le ipotesi sono la dimensione delle imprese, l'età dei lavoratori, i controlli, la sottodenuncia. Sono ipotesi, non risultati.

## Chi si fa male

L'Istat calcola il tasso anche per sesso, età e cittadinanza. Nel 2022 gli uomini avevano 14,8 infortuni gravi ogni 10.000 occupati, le donne 5,8. Fra gli uomini stranieri il tasso era 24,1, fra gli italiani 13,7. Fra i 50 e i 64 anni era 15,8, fra i 65 e gli 89 anni 26,0. Il tasso sale con l'età, e per gli uomini stranieri è quasi il doppio che per gli italiani.

## Il divario nel tempo

Dal 2018 al 2022 il Mezzogiorno scende da 14,6 a 13,0, il Centro da 12,6 a 11,9, il Nord da 10,5 a 9,6. La distanza si riduce, ma il Sud resta sopra.

<!-- figura: serie-2018-2022 -->

Per il 2026 ci sono solo le denunce all'Inail, provvisorie. Da gennaio a luglio le morti avvenute durante il lavoro, senza contare gli studenti e i tragitti casa-lavoro, sono 422, contro 432 nello stesso periodo del 2025. Nelle costruzioni sono salite da 67 a 76.

## Che cosa cambia

Ad Arezzo o a Potenza il tasso di infortuni che cambiano la vita è circa tre volte quello di Milano, e i grandi settori ne spiegano solo una parte. Vuol dire che quella distanza non è una fatalità legata al tipo di economia. È uno spazio in cui la prevenzione può ancora fare differenza.

Il dato per regione e provincia è nella [scheda degli infortuni sul lavoro mortali e con inabilità permanente](/indicatore/tasso-di-infortuni-sul-lavoro-mortali-e-con-inabilita-permanente/bes-03LAV007).

## Dati usati

- **Infortuni:** Istat, Benessere equo e sostenibile (regioni e ripartizioni ufficiali) e BES dei Territori (province), su dati Inail, 2018-2022. Per il 2026 denunce Inail provvisorie.
- **Settori:** Istat, Conti territoriali, persone occupate per branca e provincia, 2022.
- **Metodo:** regressione lineare del tasso provinciale sulle quote di occupati in agricoltura, industria in senso stretto e costruzioni. Script `scripts/articoli_trend/elab_settori_infortuni.py`.
- **Limite:** è un confronto fra province, non fra lavoratori. Le branche sono larghe. Il tasso divide gli infortuni per gli occupati residenti, mentre la regressione usa gli occupati per luogo di lavoro: nelle province da cui molti lavorano altrove il confronto è meno preciso. Gli infortuni non denunciati, più probabili nel lavoro irregolare, non sono contati.

## Fonti

- Istat, [Benessere equo e sostenibile, appendice statistica](https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip), maggio 2026.
- Istat, [Il benessere equo e sostenibile in Italia, Rapporto Bes 2025](https://www.istat.it/wp-content/uploads/2025/11/Bes-2024-Ebook.pdf).
- Istat, [Conti territoriali, occupati per branca](https://esploradati.istat.it/SDMXWS/rest/data/IT1,93_379_DF_DCCN_OCCTSEC2010_2,1.0/all?startPeriod=2021).
- Inail, [Denunce di infortuni e malattie professionali, i dati di luglio](https://www.inail.it/portale/it/inail-comunica/comunicati-stampa/comunicato-stampa.2026.09.denunce-di-infortuni-e-malattie-professionali-i-dati-inail-di-luglio.html), 8 settembre 2026.
- CIIP, [Utilizzi degli open data Inail](https://ciip-consulta.it/wp-content/uploads/2025/09/Utilizzi_Open_Data_Inail.pdf), settembre 2025.
