# Numeri verificati: `bes:04BEC006P` (Pensionati con reddito pensionistico di basso importo)

Tutti i valori vengono da `app/static/data/Assoluti_Provincia.csv` (righe con `idIndicatore` = `04BEC006P` o `04BEC005P`, `Livello/Variazione` = `Livello`, colonne `Territorio`, `Anno`, `Dato`), letti con uno script che usa solo il modulo `csv` e `statistics`. Ripartizioni e regioni dal `dossier.json` (`livelli[0].fotografia.valori`). I valori nazionali vengono da Istat (vedi `fonti.md`), non dal CSV.

## Definizione esatta
- Istat: «Percentuale di pensionati che percepiscono un reddito pensionistico lordo mensile inferiore a 500 euro sul totale dei pensionati.» (glossario dell'appendice BesT 2025, foglio `Glossario`, codice `04-04` nell'edizione 2025, `04BEC006P` nel nostro catalogo; fonte primaria Istat, Statistiche della previdenza e dell'assistenza sociale).
- Unità: percentuale, **un tasso, non un numero di persone**. Nessun totale di pensionati per provincia è nel dataset: non si possono scrivere conteggi.
- Soglia: 500 euro lordi al mese, **fissa in euro correnti** (non è indicizzata ai prezzi e non è una soglia di povertà).
- Verso nel sito: `lower_better`.

## Copertura
- 2015-2023, 9 anni. 2015 e 2016: 106 province (manca Sud Sardegna). Dal 2017: 107.
- Ultimo anno 2023 (uscito con il Bes dei territori 2025, dicembre 2025).

## Valore nazionale (Istat, appendice BesT 2025, foglio `Dominio 04`, riga Italia)
- Italia 2019: 10,4%. Italia 2023: 8,9% (-1,5 punti).
- Mezzogiorno 2019: 14,8%. Mezzogiorno 2023: 12,8% (-2,0 punti).
- Calabria 2023: 14,0% (BesT 2025 Calabria, Tavola 4).
- Trentino-Alto Adige 2023: 5,2% (BesT 2025 Trentino-Alto Adige).
- La media semplice delle 107 province nel 2023 è 8,856 (8,9), quasi uguale al 8,9 nazionale. **Non va chiamata media nazionale**: il valore nazionale è quello Istat.

## Ultimo anno (2023), 107 province
- Massimo: Crotone 16,9. Minimo: Bolzano 4,1. Distanza 12,8 punti, rapporto 4,1 volte (16,9 / 4,1 = 4,12).
- Mediana 8,1. Media semplice 8,856. Le province sopra il valore Italia (8,9): 46. Province con almeno 12,0: 22. Province con al massimo 6,0: 19.
- 5 più alte: Crotone 16,9, Barletta-Andria-Trani 15,9, Napoli 15,6, Agrigento 15,4, Cosenza 14,5.
- 5 più basse (dal fondo): Bolzano 4,1, Biella 4,9, Bologna 5,4, Ferrara 5,4, Novara 5,4 (tre a pari merito a 5,4: per l'ordinale vale la regola del sito).
- Posizioni per valore (1 = più alto): Crotone 1, Napoli 3, Enna 13, Roma 32, Cagliari 37, Milano 90, Biella 106, Bolzano 107.
- Le prime 10 province per valore sono tutte del Mezzogiorno. Le prime 20 sono tutte del Mezzogiorno. Nelle prime 25 ce ne sono 24 (la venticinquesima è fuori dal Mezzogiorno). Fra le ultime 20 (le più basse): 18 del Nord e 2 del Centro.
- Per ripartizione (media semplice delle province, solo descrittiva): Mezzogiorno 38 province, media 12,24, da 9,2 (Isernia) a 16,9 (Crotone). Centro 22, media 8,14, da 5,6 a 12,1 (Latina). Nord 47, media 6,45, da 4,1 a 8,9 (Verbano-Cusio-Ossola). La provincia meridionale con il valore più basso (Isernia, 9,2) sta sopra la più alta del Nord (8,9).

## Serie 2015-2023 (tutte le 107, 106 nel 2015-2016)
| Anno | Media semplice | Mediana | Minimo | Massimo | Distanza |
|---|---|---|---|---|---|
| 2015 | 10,616 | 9,35 | Ferrara 6,1 | Crotone 19,3 | 13,2 |
| 2016 | 10,715 | 9,5 | Ferrara 6,2 | Crotone 19,5 | 13,3 |
| 2017 | 10,712 | 9,5 | Ferrara 6,2 | Crotone 19,6 | 13,4 |
| 2018 | 10,38 | 9,5 | Biella 6,1 | Crotone 18,8 | 12,7 |
| 2019 | 10,301 | 9,4 | Biella 6,1 | Crotone 19,0 | 12,9 |
| 2020 | 9,637 | 9,0 | Biella 5,5 | Crotone 17,8 | 12,3 |
| 2021 | 9,567 | 8,8 | Biella 5,4 | Crotone 17,7 | 12,3 |
| 2022 | 9,213 | 8,4 | Biella 5,1 | Crotone 16,8 | 11,7 |
| 2023 | 8,856 | 8,1 | Bolzano 4,1 | Crotone 16,9 | 12,8 |

- Fra il 2015 e il 2023 il valore **scende in tutte le 106 province con dato in entrambi gli anni** (nessuna sale). Calo massimo Palermo -4,9 punti, minimo Reggio Calabria -0,2 punti. Crotone 19,3 -> 16,9 (-2,4). Napoli 18,9 -> 15,6 (-3,3). Enna 17,6 -> 12,8 (-4,8). Cagliari 13,6 -> 10,0 (-3,6). Roma 11,8 -> 10,5 (-1,3). Milano 7,4 -> 6,0 (-1,4). Biella 6,4 -> 4,9 (-1,5). Bolzano 8,6 -> 4,1 (-4,5).
- La distanza fra massimo e minimo resta fra 11,7 e 13,4 punti in tutto il periodo: nel 2015 è 13,2, nel 2023 è 12,8. L'estremo alto scende di 2,4 punti, quello basso di 2,0 (6,1 -> 4,1, ma sono due province diverse, Ferrara e Bolzano). Per dire "la distanza non si chiude" confronta le distanze, non due province.
- Il 2023 di Bolzano è uno scarto brusco: 6,9 nel 2022 e 4,1 nel 2023 (-2,8 in un anno). **Non so se sia un cambio della serie o un fatto reale.** Non scriverlo nel pezzo come tendenza senza una fonte. Fra il 2022 e il 2023 la variazione media è -0,36 punti e una sola provincia su 107 sale.
- Stesso periodo, l'estremo basso cambia nome tre volte (Ferrara, Biella, Bolzano): è una conseguenza dei decimali, non una storia.

## Confronto solo come numero con `bes:04BEC005P` (importo medio annuo pro-capite dei redditi pensionistici, euro)
Definizione Istat: rapporto tra l'importo complessivo delle pensioni erogate nell'anno (euro) e il numero dei pensionati.
- 2023: Crotone 16.309 euro (minimo, anche per questo indicatore), Milano 26.348,5 euro (massimo). Media semplice 21.108,8, mediana 21.502,9. Italia (Istat, appendice) 21.736,8 euro, 2019: 19.110,7.
- Crotone ha la quota più alta di pensionati sotto i 500 euro (16,9) e l'importo medio più basso (16.309). Milano ha la quota 6,0 e l'importo più alto. Bolzano ha la quota più bassa e un importo 23.315,4.
- Salto 2022 -> 2023 dell'importo: la media semplice sale da 19.687,2 a 21.108,8 euro, +7,2% in un anno, contro +2,7% del 2022 sul 2021 (19.162,0 -> 19.687,2). **Il motivo non è nelle fonti aperte**: non scriverlo come causa. Stesso anno in cui la quota bassa scende.
- Non farne una tesi: sono due misure sullo stesso fenomeno, non due indicatori indipendenti.

## Cosa NON ricavare da questi numeri
- Nessun numero di persone: non c'è la popolazione dei pensionati per provincia nel dataset.
- Il 16,9% di Crotone non è «uno su sei vive con meno di 500 euro»: è la quota di titolari di pensione che hanno un reddito pensionistico lordo sotto i 500 euro al mese, vedi limiti in `fonti.md`.
