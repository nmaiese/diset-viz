---
title: 'Giovani morti in strada: il Nord è migliorato di più, e al Sud un incidente uccide più spesso'
seo_title: 'Giovani morti in strada: dove un incidente uccide di più'
slug: giovani-morti-in-strada-nord-sud
description: Mortalità stradale fra 15 e 34 anni giù di due terzi in vent'anni, più al Nord che al Sud. E al Sud un incidente fuori città è più spesso mortale.
date: 2026-09-23
author: Redazione Divario Italia
cover: /static/img/blog/giovani-morti-in-strada-nord-sud.jpg
cover_alt: Un lungo rettilineo della strada statale 131 in Sardegna, fra colline boscose, con un camion e alcune auto.
cover_caption: La statale 131 Diramazione Centrale Nuorese, in Sardegna.
cover_credit:
  author: m/m
  license: CC BY-SA 4.0
  license_url: https://creativecommons.org/licenses/by-sa/4.0
  source_url: https://commons.wikimedia.org/wiki/File:SS131DCN-7602.jpg
  source_name: Wikimedia Commons
  changes: Ritagliata e ridimensionata
tags:
- Salute
- Sicurezza stradale
- Divario Nord-Sud
indicator: bes-01SAL005
indicator_label: Mortalità per incidenti stradali (15-34 anni)
trend:
  topic: sicurezza-stradale
  detected: 2026-09-23
  ranking: data/trend/2026-09-23/ranking.json
  score:
    interest: 0.71
    data: 0.9
    story: 1.0
    total: 0.674
    rank: 11
  signals:
  - type: google_trends_tendenza
    text: autovelox (500+ ricerche, fra le tendenze del giorno)
    source: Google Trends, ricerche di tendenza, Italia
    url: https://trends.google.com/trending?geo=IT
    date: 2026-09-22
  - type: google_news_principali
    text: Torino, morto bambino di 7 anni investito mentre era in bici (Sky TG24)
    source: Google News Italia, notizie principali
    url: https://news.google.com/rss/articles/CBMif0FVX3lxTE1BVDB6dGdCeDZuUms3S0ZSME5hZWZIRUwtTHZqb2N6aG1QT1RpaHdOTVdFa0I2N044N0FESTFCVjdBQ0RjdUNWTEJabjFNckZnRF9POUxjTC03b1dyNlhaeGhDTXRzMHkyd00tVUpsYnhFNEJlbnB
    date: 2026-09-22
  - type: google_trends_interesse
    text: 'autovelox: interesse degli ultimi 7 giorni 0,65 volte la media degli 83 precedenti. Regioni con piu'' interesse: Abruzzo, Sardegna, Molise'
    source: Google Trends (pytrends), Italia, finestra today 3-m e now 7-d
    url: https://trends.google.com/trends/explore?geo=IT&q=autovelox
    date: 2026-09-23
  - type: google_trends_interesse
    text: 'incidente stradale: interesse degli ultimi 7 giorni 0,85 volte la media degli 83 precedenti. Regioni con piu'' interesse: Calabria, Sardegna, Puglia'
    source: Google Trends (pytrends), Italia, finestra today 3-m e now 7-d
    url: https://trends.google.com/trends/explore?geo=IT&q=incidente%20stradale
    date: 2026-09-23
dataset:
  name: Mortalità stradale dei giovani, letalità degli incidenti extraurbani e tempi dei soccorsi, per regione
  description: Tasso di mortalità per incidenti stradali fra i 15 e i 34 anni per regione e ripartizione (2004-2024), morti ogni 100 incidenti sulle strade extraurbane per provincia (2015-2023) e media per regione (2021-2023), tempo di arrivo dei mezzi di soccorso per regione (2022).
  method: 'Mortalità: dati Istat senza rielaborazione, compresi i valori ufficiali per Italia e ripartizioni. Letalità extraurbana per regione: media semplice delle province 2021-2023, elaborazione Divario Italia (scripts/articoli_trend/elab_media_province.py). Tempi dei soccorsi: indicatore D09Z del Nuovo sistema di garanzia, trascritto dalla Relazione 2022 del ministero della Salute.'
  temporal: 2004/2024
  spatial: Italia, ripartizioni, regioni e province
  creator: Istat, Ministero della Salute
  source_url: https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip
  download: /static/data/articles/giovani-morti-in-strada-nord-sud.csv
external_figures:
- value: 11,8
  what: calo percentuale dei morti in incidenti stradali nel Sud continentale (Isole escluse), tutte le età, 2025
  source: Istat, Incidenti stradali anno 2025, 24 luglio 2026
  url: https://www.istat.it/wp-content/uploads/2026/07/REPORT_INCIDENTI_STRADALI_2025.pdf
- value: 3,6
  what: morti ogni 100 incidenti sulle strade extraurbane, 2025
  source: Istat, Incidenti stradali anno 2025, 24 luglio 2026
  url: https://www.istat.it/wp-content/uploads/2026/07/REPORT_INCIDENTI_STRADALI_2025.pdf
- value: 0,9
  what: morti ogni 100 incidenti sulle strade urbane, 2025
  source: Istat, Incidenti stradali anno 2025, 24 luglio 2026
  url: https://www.istat.it/wp-content/uploads/2026/07/REPORT_INCIDENTI_STRADALI_2025.pdf
- value: 3,1
  what: morti ogni 100 incidenti nei comuni delle aree interne, 2024
  source: Istat, convegno del 16 dicembre 2025, relazione Palumbo e Carucci
  url: https://www.istat.it/wp-content/uploads/2025/12/PALUMBO_CARUCCI16dicembre2025.pdf
- value: 1,5
  what: morti ogni 100 incidenti nei comuni dei centri, 2024
  source: Istat, convegno del 16 dicembre 2025, relazione Palumbo e Carucci
  url: https://www.istat.it/wp-content/uploads/2025/12/PALUMBO_CARUCCI16dicembre2025.pdf
- value: '18'
  what: quota percentuale che usa sempre la cintura posteriore al Sud, PASSI 2023-2024
  source: Istituto superiore di sanità, sorveglianza PASSI, via Quotidiano Sanità, 24 ottobre 2025
  url: https://www.quotidianosanita.it/studi-e-analisi/sicurezza-stradale-iss-solo-uno-su-usa-cinture-posteriori-cresce-uso-dispositivi-per-i-beb/
- value: '54'
  what: quota percentuale che usa sempre la cintura posteriore al Nord, PASSI 2023-2024
  source: Istituto superiore di sanità, sorveglianza PASSI, via Quotidiano Sanità, 24 ottobre 2025
  url: https://www.quotidianosanita.it/studi-e-analisi/sicurezza-stradale-iss-solo-uno-su-usa-cinture-posteriori-cresce-uso-dispositivi-per-i-beb/
- value: '93'
  what: quota percentuale che usa sempre il casco al Sud, PASSI 2023-2024
  source: Istituto superiore di sanità, sorveglianza PASSI, via Quotidiano Sanità, 24 ottobre 2025
  url: https://www.quotidianosanita.it/studi-e-analisi/sicurezza-stradale-iss-solo-uno-su-usa-cinture-posteriori-cresce-uso-dispositivi-per-i-beb/
- value: '98'
  what: quota percentuale che usa sempre il casco al Nord, PASSI 2023-2024
  source: Istituto superiore di sanità, sorveglianza PASSI, via Quotidiano Sanità, 24 ottobre 2025
  url: https://www.quotidianosanita.it/studi-e-analisi/sicurezza-stradale-iss-solo-uno-su-usa-cinture-posteriori-cresce-uso-dispositivi-per-i-beb/
- value: '37'
  what: quota percentuale della velocità eccessiva sulle violazioni sanzionate, 2025
  source: Istat, Incidenti stradali in Italia, anno 2025, 24 luglio 2026
  url: https://www.istat.it/comunicato-stampa/incidenti-stradali-in-italia-2025/
- value: 5,5
  what: morti ogni 100 incidenti su strade extraurbane in Sardegna, 2023
  source: Istat, BesT 2025, Sardegna
  url: https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Sardegna.pdf
- value: 4,1
  what: morti ogni 100 incidenti su strade extraurbane in Italia, 2023
  source: Istat, BesT 2025, Sardegna
  url: https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Sardegna.pdf
- value: 2,8
  what: calo percentuale dei morti in incidenti stradali nelle Isole, tutte le età, 2025
  source: Istat, Incidenti stradali anno 2025, 24 luglio 2026
  url: https://www.istat.it/wp-content/uploads/2026/07/REPORT_INCIDENTI_STRADALI_2025.pdf
---

In questi giorni "autovelox" è fra le ricerche in crescita su Google, e a Torino un bambino di sette anni è morto investito mentre andava in bicicletta. Di strade si parla molto, quasi sempre in termini di multe o di singoli incidenti. I dati degli ultimi vent'anni raccontano altro: una delle storie di maggior successo della sicurezza italiana, che però non ha premiato tutti allo stesso modo.

Nel 2004 morivano in un incidente stradale **2,0 giovani ogni 10.000 al Nord** e 1,4 nel Mezzogiorno, fra i 15 e i 34 anni. Nel 2024 il Nord è sceso a 0,5, il Mezzogiorno a 0,8.
{: .data-callout}

## In breve

- In Italia la mortalità stradale dei giovani è scesa da 1,8 a 0,6 ogni 10.000, due terzi in meno in vent'anni.
- Il Centro-Nord, che partiva peggio, è migliorato di più. Per dieci anni le tre aree sono rimaste quasi alla pari, e nel 2024 il Mezzogiorno è salito nettamente sopra per la prima volta.
- Al Sud un incidente fuori città è più spesso mortale. È la differenza più stabile, e non dipende da un anno solo.

## Vent'anni in una figura

La serie Istat, con i valori ufficiali per ripartizione, mostra un crollo generale. Il Nord passa da 2,0 a 0,5 morti ogni 10.000 giovani, il Centro da 2,0 a 0,6, il Mezzogiorno da 1,4 a 0,8. Nel 2004 il rischio più alto era al Centro-Nord. Dal 2013 al 2023 le tre aree oscillano tutte fra 0,5 e 0,8, e nessuna si stacca davvero.

<!-- figura: serie-2004-2024 -->

## Il 2024, un anno da maneggiare con cura

Il sorpasso del Sud è concentrato in un anno. La Sardegna passa da 0,8 a 1,3, la Calabria da 0,5 a 0,9. In regioni piccole bastano pochi casi per muovere il tasso. I primi dati sul 2025, che l'Istat per ora pubblica solo per tutte le età e in numeri assoluti, danno segnali diversi: nel Sud continentale i morti in strada calano dell'11,8%, nelle Isole solo del 2,8%. Se il 2024 sia stato un picco lo dirà la serie per età del 2025, che non c'è ancora.

<!-- figura: regioni-2024 -->

## Incidenti più gravi

C'è però una differenza stabile, e non dipende da un anno solo. È la gravità. L'Istat la misura con l'indice di mortalità, i morti ogni 100 incidenti con feriti. Nel 2025 in Italia era 3,6 sulle strade extraurbane e 0,9 su quelle urbane. Fuori città le velocità sono più alte, e un urto è più grave.

Al Sud questa gravità pesa di più. Nel 2023, facendo la media delle province, sulle strade extraurbane ci sono 5,66 morti ogni 100 incidenti nel Mezzogiorno e 3,70 nel Centro-Nord. In Sardegna l'indice ufficiale è 5,5, contro 4,1 in Italia. Ci sono eccezioni: la provincia con il valore più alto è Asti, in Piemonte, con 10,8.

Conta anche la distanza. Nel 2024, in tutta Italia, nei comuni delle aree interne, lontani dai servizi, l'Istat ha contato 3,1 morti ogni 100 incidenti contro 1,5 nei centri.

## Il soccorso, le cinture

Abbiamo provato a mettere accanto a questi numeri il tempo che passa fra la chiamata d'emergenza e l'arrivo dei soccorsi, che il ministero della Salute misura regione per regione per tutte le emergenze, non solo per gli incidenti. Nel 2022 andava dai 15 minuti dell'Emilia-Romagna ai 28 della Calabria, con 26 in Basilicata e 25 in Sardegna. In Italia 19.

<!-- figura: soccorsi-letalita -->

Il legame sembra esserci, ma sta tutto nella differenza fra Nord e Sud. Dentro il Centro-Nord, e dentro il Mezzogiorno, i tempi dei soccorsi e la gravità degli incidenti non vanno insieme: la Valle d'Aosta ha soccorsi lenti e incidenti poco letali, il Piemonte il contrario. Qualunque cosa distingua il Sud dal Nord darebbe lo stesso disegno. E messo accanto alla mortalità dei giovani, il tempo dei soccorsi non mostra un legame stabile da un anno all'altro. Non è una spiegazione, e non la presentiamo come tale.

Le abitudini contano. Secondo la sorveglianza PASSI dell'Istituto superiore di sanità, nel 2023-2024 usava sempre la cintura sul sedile posteriore il 18% delle persone al Sud e il 54% al Nord. Il casco in moto il 93% contro il 98%.

## Che cosa cambia per chi ha vent'anni

Le ricerche sugli autovelox di questi giorni parlano soprattutto di multe. La velocità resta la violazione più sanzionata dopo la sosta vietata, il 37% del totale. Ma per un ragazzo sardo o calabrese il rischio dipende anche da dove guida: fuori città, al Sud, un incidente finisce più spesso con un morto, e la cintura dietro la usa meno di una persona su cinque.

L'indicatore anno per anno è nella [scheda della mortalità per incidenti stradali](/indicatore/mortalita-per-incidenti-stradali-15-34-anni/bes-01SAL005), il dato provinciale nella [scheda della mortalità stradale extraurbana](/indicatore/mortalita-stradale-in-ambito-extraurbano/bes-07SIC008P).

## Dati usati

- **Mortalità dei giovani:** Istat, Benessere equo e sostenibile, aggiornamento intermedio 2026. Tasso standardizzato per 10.000 residenti di 15-34 anni, regioni e ripartizioni ufficiali, dal 2004 al 2024.
- **Gravità degli incidenti:** Istat, BES dei Territori, morti ogni 100 incidenti su strade extraurbane per provincia, 2015-2023. Per il confronto fra regioni usiamo la media delle province 2021-2023, che non è il valore regionale ufficiale.
- **Tempi dei soccorsi:** ministero della Salute, Nuovo sistema di garanzia, indicatore D09Z (intervallo allarme-target, tutte le emergenze sanitarie), 2022. Le correlazioni fra regioni sono in un file del dossier del pezzo.
- **Limite:** i tassi regionali poggiano su numeri piccoli. Un confronto fra regioni dice se due fenomeni si muovono insieme, non che uno causa l'altro.

## Fonti

- Istat, [Incidenti stradali, anno 2025](https://www.istat.it/wp-content/uploads/2026/07/REPORT_INCIDENTI_STRADALI_2025.pdf), 24 luglio 2026.
- Istat, [Incidenti stradali in Italia 2025, comunicato](https://www.istat.it/comunicato-stampa/incidenti-stradali-in-italia-2025/), 24 luglio 2026.
- Istat, [Benessere equo e sostenibile, appendice statistica](https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip), maggio 2026.
- Istat, [BesT 2025, Sardegna](https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Sardegna.pdf), dicembre 2025.
- Istat, [Incidentalità nelle aree interne](https://www.istat.it/wp-content/uploads/2025/12/PALUMBO_CARUCCI16dicembre2025.pdf), convegno del 16 dicembre 2025.
- Ministero della Salute, [Monitoraggio dei LEA, Relazione 2022](https://www.camera.it/temiap/2024/09/23/OCD177-7562.pdf).
- Quotidiano Sanità, [Sicurezza stradale, i dati PASSI dell'Iss](https://www.quotidianosanita.it/studi-e-analisi/sicurezza-stradale-iss-solo-uno-su-usa-cinture-posteriori-cresce-uso-dispositivi-per-i-beb/), 24 ottobre 2025.
