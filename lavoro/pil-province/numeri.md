# Numeri provinciali disponibili e limite 2024

## Anno 2024

Valori 2024 di PIL pro capite per provincia: non disponibili nel rilascio Istat aperto. Il rapporto Istat 2022-2024 diffonde PIL provinciale e valore aggiunto ai prezzi correnti per 2022 e 2023; le stime provinciali 2024 non sono pubblicate. Inoltre, il repository non contiene righe `ter-901` o `ter-902` provinciali.

Comando eseguito per controllare i dati locali:

```sh
rg '^901;|^902;' app/static/data/Assoluti_Provincia.csv
```

Risultato: nessuna riga. Il CSV non consente di fornire né le prime/ultime cinque province 2024 né distanza PIL-reddito provinciale. Il reddito disponibile familiare del rilascio 2024 è regionale, non provinciale.

## Ultimo anno provinciale pubblicato da Istat: 2023

Il rapporto Istat del 22 dicembre 2025 pubblica esplicitamente i primi cinque e gli ultimi cinque valori, in migliaia di euro correnti. Questi sono gli estremi reperibili senza inventare osservazioni mancanti. I valori sotto riprendono le cifre pubblicate, convertite in euro moltiplicando per 1.000; non sono precisione al singolo euro.

| Gruppo | Provincia | PIL pro capite 2023, euro correnti |
|---|---|---:|
| prime 5 | Milano | 71.300 |
| prime 5 | Provincia autonoma di Bolzano/Bozen | 61.500 |
| prime 5 | Bologna | 50.100 |
| prime 5 | Modena | 48.600 |
| prime 5 | Roma | 47.600 |
| ultime 5 | Barletta-Andria-Trani | 19.800 |
| ultime 5 | Sud Sardegna | 19.500 |
| ultime 5 | Cosenza | 19.400 |
| ultime 5 | Enna | 19.300 |
| ultime 5 | Agrigento | 19.000 |

Rapporto fra gli estremi pubblicati: 71,3 / 19,0 = circa 3,75. Calcolo sui due valori Istat arrotondati a un decimo di migliaio di euro, quindi rapporto indicativo, non ricalcolato su valori non arrotondati.

Fonte e verifica: Istat, “Conti economici territoriali 2022-2024”, PDF, pagina 6, pubblicato il 22 dicembre 2025. URL aperto: https://www.istat.it/wp-content/uploads/2025/12/REPORT-CONTI-TERRITORIALI_Anni-2022-2024.pdf. Citazione: «Nel 2023 la provincia con il Pil pro-capite più elevato, calcolato a prezzi correnti, è stata Milano, con 71,3mila euro». Per i valori inferiori: «All’estremo opposto della graduatoria si colloca Agrigento, con un Pil per abitante pari a 19mila euro».

Comando locale che mostra l’assenza dei dati provinciali del sito, da ripetere dalla radice del repository:

```sh
rg '^901;|^902;' app/static/data/Assoluti_Provincia.csv
```

Righe CSV: nessuna. I valori 2023 della tabella vengono dal PDF Istat, non da un CSV locale. Non ho creato né modificato dati del sito.

## Distanza PIL-reddito

Non calcolabile per provincia con i dati verificati. In questo rilascio Istat il PIL provinciale arriva al 2023, mentre il reddito disponibile delle famiglie è diffuso per regione. Nel CSV provinciale del repository non esistono righe `ter-901` o `ter-902`. Non attribuire una distanza provinciale usando dati regionali o fonti con anni diversi.
