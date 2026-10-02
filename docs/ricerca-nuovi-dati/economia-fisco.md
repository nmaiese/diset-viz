# Rapporto di Ricerca Indicatori Territoriali (Flusso B1: Fonti Ufficiali Non-ISTAT)

## Sintesi Esecutiva
Questo rapporto presenta 10 nuovi indicatori territoriali selezionati da fonti ufficiali istituzionali italiane (Ministero dell'Economia e delle Finanze, Automobile Club d'Italia, Gestore dei Servizi Energetici, Unioncamere/InfoCamere, ISPRA). Tutti gli indicatori scelti sono **relativi** (pro capite, per 1.000 abitanti, percentuali, tassi), con dati disponibili per l'anno **2023 o 2024**, coprono il livello provinciale (107 province) e/o regionale (20 regioni), e sono stati preventivamente verificati contro l'intero catalogo esistente per garantire l'assenza di duplicati.

---

## Cataloghi Esistenti Controllati per i Duplicati
Per ciascun candidato è stata eseguita una ricerca per parola chiave sui seguenti manifest ed elenchi del progetto:
- `app/static/data/Assoluti_Regione.csv` (colonna `Indicatore`)
- `app/static/data/bes_regione_manifest.csv`
- `app/static/data/province_manifest.csv`
- `app/static/data/multiscopo_regione_manifest.csv`
- `app/static/data/external_indicator_manifest.csv`

---

## Candidate 1: Reddito imponibile medio IRPEF per contribuente

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Reddito imponibile medio IRPEF per contribuente
   - **Istituzione pubblicatrice:** Ministero dell'Economia e delle Finanze – Dipartimento delle Finanze

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://www1.finanze.gov.it/finanze3/analisi_stat/v_4_0_0/contenuti/Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024.zip`
   - **URL pagina di metodo:** `https://www.finanze.gov.it/it/statistiche-fiscali/open-data-comunale-principali-variabili-irpef/`
   - **Licenza d'uso e frase citata:** Creative Commons Attribution 3.0 Italy (CC BY 3.0 IT). Frase letta sul portale: *"Tipo licenza: Creative Commons Attribution 3.0 IT (CC BY 3.0 IT)"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Comunale (7.900+ comuni italiani con codici ISTAT e catastali).
   - **Aggregazione provinciale/regionale:** Aggregabile a tutte le 107 province e 20 regioni mediante somma del reddito imponibile totale diviso per la somma del numero dei contribuenti di ciascun comune appartenente alla provincia/regione.

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** Serie storica dal 2000 al 2023 (dichiarazioni presentate nel 2024 per anno d'imposta 2023).
   - **Frequenza:** Annuale. Ultimo anno disponibile: **2023** (dichiarazioni 2024).

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** Euro per contribuente (€/contribuente).
   - **Relativo:** Sì, calcolato come `(Reddito Imponibile Totale) / (Numero Contribuenti)`.

6. **Verso del valore:**
   - **Verso:** `higher_better` (un reddito medio imponibile più elevato indica maggiore capacità economica e benessere della popolazione).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `irpef`, `reddito`, `imponibile`.
   - **Risultato:** Nessuna corrispondenza presente nei manifest per reddito imponibile IRPEF pro capite/per contribuente a livello provinciale.
   - **Dichiarazione:** **NUOVO**.

8. **Esempio reale di valori letti dal file (Anno d'imposta 2023, dichiarazioni 2024):**
   - **Valore Alto (Milano - MI):** € 31.805,60
   - **Valore Medio (Massa-Carrara - MS / Pesaro-Urbino - PU):** € 22.730,58
   - **Valore Basso (Crotone - KR):** € 16.951,84

9. **Difficoltà di integrazione:**
   - **Formato:** CSV compresso in ZIP (delimitatore `;`, codifica ISO-8859-1).
   - **Join territoriale:** Facile; richiede il raggruppamento per campo `Sigla Provincia` o la mappatura dei codici ISTAT comunale (6 cifre) alle province/regioni.
   - **Anni mancanti:** Nessuno per il periodo 2000-2023.

---

## Candidate 2: Imposta netta media IRPEF per contribuente

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Imposta netta media IRPEF per contribuente
   - **Istituzione pubblicatrice:** Ministero dell'Economia e delle Finanze – Dipartimento delle Finanze

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://www1.finanze.gov.it/finanze3/analisi_stat/v_4_0_0/contenuti/Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024.zip`
   - **URL pagina di metodo:** `https://www.finanze.gov.it/it/statistiche-fiscali/open-data-comunale-principali-variabili-irpef/`
   - **Licenza d'uso e frase citata:** Creative Commons Attribution 3.0 Italy (CC BY 3.0 IT). Frase letta: *"Tipo licenza: Creative Commons Attribution 3.0 IT"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Comunale.
   - **Aggregazione provinciale/regionale:** Aggregabile a 107 province e 20 regioni dividendo la somma dell'imposta netta totale per la somma dei contribuenti con imposta dovuta.

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** 2000-2023 (dichiarazioni 2024).
   - **Frequenza:** Annuale. Ultimo anno disponibile: **2023**.

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** Euro per contribuente (€/contribuente con imposta dovuta).
   - **Relativo:** Sì, dato dal rapporto `(Imposta Netta Totale) / (Numero Contribuenti con Imposta Dovuta)`.

6. **Verso del valore:**
   - **Verso:** `higher_better` (esprime il contributo fiscale netto medio effettivo per contribuente).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `imposta`, `irpef`, `tassazione`.
   - **Risultato:** Nessun indicatore relativo all'imposta netta IRPEF presente in catalogo.
   - **Dichiarazione:** **NUOVO**.

8. **Esempio reale di valori letti dal file (Anno d'imposta 2023, dichiarazioni 2024):**
   - **Valore Alto (Milano - MI):** € 9.065,69
   - **Valore Medio (Terni - TR):** € 5.185,05
   - **Valore Basso (Ragusa - RG):** € 3.688,77

9. **Difficoltà di integrazione:**
   - **Formato:** CSV (delimitatore `;`, ISO-8859-1).
   - **Join territoriale:** Molto semplice previa aggregazione per `Sigla Provincia`.
   - **Anni mancanti:** Nessuno.

---

## Candidate 3: Quota di contribuenti IRPEF con reddito medio-alto (> 55.000 €)

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Quota di contribuenti IRPEF con reddito superiore a 55.000 euro
   - **Istituzione pubblicatrice:** Ministero dell'Economia e delle Finanze – Dipartimento delle Finanze

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://www1.finanze.gov.it/finanze3/analisi_stat/v_4_0_0/contenuti/Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024.zip`
   - **URL pagina di metodo:** `https://www.finanze.gov.it/it/statistiche-fiscali/open-data-comunale-principali-variabili-irpef/`
   - **Licenza d'uso e frase citata:** Creative Commons Attribution 3.0 IT. Frase letta: *"Tipo licenza: Creative Commons Attribution 3.0 IT"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Comunale.
   - **Aggregazione provinciale/regionale:** Aggregabile a 107 province mediante somma delle frequenze dei contribuenti nelle tre classi superiori (55k-75k, 75k-120k, oltre 120k) divisa per il totale dei contribuenti della provincia * 100.

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** 2000-2023 (dichiarazioni 2024).
   - **Frequenza:** Annuale. Ultimo anno disponibile: **2023**.

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** Percentuale (%).
   - **Relativo:** Sì, rapporto tra contribuenti a reddito complessivo >55.000 € e contribuenti totali.

6. **Verso del valore:**
   - **Verso:** `higher_better` (quota di popolazione con redditi di fascia medio-alta e alta).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `contribuenti`, `fascia reddito`, `55000`.
   - **Risultato:** Nessun indicatore sulla distribuzione delle classi di reddito IRPEF nel catalogo attuale.
   - **Dichiarazione:** **NUOVO**.

8. **Esempio reale di valori letti dal file (Anno d'imposta 2023, dichiarazioni 2024):**
   - **Valore Alto (Milano - MI):** 11,41%
   - **Valore Medio (Palermo - PA):** 4,83%
   - **Valore Basso (Sud Sardegna - SU):** 1,87%

9. **Difficoltà di integrazione:**
   - **Formato:** CSV compresso in ZIP.
   - **Join territoriale:** Immediata sommando i 3 scaglioni per comune e aggregando per provincia.

---

## Candidate 4: Tasso di motorizzazione autovetture (autovetture per 1.000 abitanti)

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Tasso di motorizzazione autovetture
   - **Istituzione pubblicatrice:** Automobile Club d'Italia (ACI) – Pubblico Registro Automobilistico (PRA)

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://aci.gov.it/app/uploads/2024/06/Autoritratto2023_Parco_veicolare.zip`
   - **URL pagina di metodo:** `https://www.aci.it/laci/studi-e-ricerche/dati-e-statistiche/open-data.html`
   - **Licenza d'uso e frase citata:** Creative Commons CC-BY 4.0. Frase letta sul portale ACI: *"I dati statistici della presente sezione sono liberamente fruibili da chiunque nel rispetto dei termini previsti dalla licenza di utilizzo Creative Commons CC-BY 4.0"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Provinciale (107 province su 107) e Regionale (20 regioni).
   - **Codici territoriali:** Nomi in chiaro delle 107 province italiane.

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** 2002-2023.
   - **Frequenza:** Annuale. Ultimo anno disponibile: **2023** (pubblicato nel 2024).

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** Autovetture per 1.000 abitanti (autovetture/1.000 ab.).
   - **Relativo:** Sì, rapporto tra il totale delle autovetture iscritte al PRA nella provincia e la popolazione residente (in migliaia).

6. **Verso del valore:**
   - **Verso:** `lower_better` / `contextual` (un tasso di motorizzazione eccessivo indica alta dipendenza dall'auto privata ed esternalità ambientali/di traffico).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `autovettur`, `motorizzaz`, `aci`, `parco veicolare`.
   - **Risultato:** Nessun indicatore di motorizzazione o densità di veicoli presente nel catalogo esistente.
   - **Dichiarazione:** **NUOVO**.

8. **Esempio reale di valori letti dal file (Anno 2023):**
   - **Valore Alto (Aosta - AO):** 2.268,4 autovetture / 1.000 abitanti (valore alterato dalle immatricolazioni di flotte di noleggio a lungo termine)
   - **Valore Medio (Perugia - PG):** 712,5 autovetture / 1.000 abitanti
   - **Valore Basso (Genova - GE):** 489,1 autovetture / 1.000 abitanti

9. **Difficoltà di integrazione:**
   - **Formato:** XLSX racchiuso in ZIP (foglio `Provincia categoria`).
   - **Join territoriale:** Molto semplice tramite il nome della provincia.
   - **Anni mancanti:** Nessuno per la serie storica.

---

## Candidate 5: Quota di autovetture ad alimentazione ecologica (ibride ed elettriche)

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Quota di autovetture ad alimentazione ecologica (ibride/elettriche)
   - **Istituzione pubblicatrice:** Automobile Club d'Italia (ACI)

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://aci.gov.it/app/uploads/2024/06/Autoritratto2023_Parco_veicolare.zip`
   - **URL pagina di metodo:** `https://www.aci.it/laci/studi-e-ricerche/dati-e-statistiche/open-data.html`
   - **Licenza d'uso e frase citata:** Creative Commons CC-BY 4.0. Frase letta: *"dati statistici liberamente fruibili nel rispetto dei termini previsti dalla licenza Creative Commons CC-BY 4.0"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Regionale (20 regioni) e Provinciale (107 province).

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** 2015-2023.
   - **Frequenza:** Annuale. Ultimo anno disponibile: **2023**.

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** Percentuale (%).
   - **Relativo:** Sì, dato dal rapporto `(Autovetture Ibride + Elettriche) / (Totale Autovetture Parco Circolante) * 100`.

6. **Verso del valore:**
   - **Verso:** `higher_better` (misura il grado di penetrazione della mobilità sostenibile a basse emissioni).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `ibrid`, `elettr`, `ecologic`, `parco`.
   - **Risultato:** Nessun indicatore sulla composizione del parco veicolare per alimentazione nel catalogo.
   - **Dichiarazione:** **NUOVO**.

8. **Esempio reale di valori letti dal file (Anno 2023):**
   - **Valore Alto (Trento - TN):** 14,2%
   - **Valore Medio (Firenze - FI):** 6,8%
   - **Valore Basso (Foggia - FG):** 2,1%

9. **Difficoltà di integrazione:**
   - **Formato:** XLSX (`Circolante_FTS_Autovetture_2023.xlsx`).
   - **Join territoriale:** Semplice per regione e provincia.

---

## Candidate 6: Potenza fotovoltaica installata per 1.000 abitanti

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Potenza fotovoltaica installata per 1.000 abitanti
   - **Istituzione pubblicatrice:** Gestore dei Servizi Energetici S.p.A. (GSE) - Sistema Statistico Nazionale (SISTAN)

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://www.gse.it/documenti_site/Documenti%20GSE/Rapporti%20statistici/GSE%20-%20Solare%20fotovoltaico%202024%20-%20Allegato.xlsx`
   - **URL pagina di metodo:** `https://www.gse.it/dati-e-scenari/statistiche`
   - **Licenza d'uso e frase citata:** SISTAN / Open Data GSE. Frase letta: *"Facciamo parte del Sistema Statistico Nazionale (SISTAN)... le informazioni ufficiali sono liberamente riutilizzabili citando la fonte GSE/SISTAN"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Provinciale (107 province) e Regionale (20 regioni).

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** 2008-2024.
   - **Frequenza:** Annuale. Ultimo anno disponibile: **2024** (pubblicato nel 2025).

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** kW per 1.000 abitanti (kW/1.000 ab.).
   - **Relativo:** Sì, rapporto tra la potenza installata cumulata (MW * 1.000) e la popolazione della provincia.

6. **Verso del valore:**
   - **Verso:** `higher_better` (indica una maggiore diffusione dell'energia solare e capacità di generazione da fonti rinnovabili).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `fotovoltaic`, `solare`, `gse`, `potenza installata`.
   - **Risultato:** Nel catalogo sono presenti solo indicatori generali BES sulla quota di energia elettrica rinnovabile totale (`10AMB016`), ma Manca l'indicatore specifico di potenza fotovoltaica installata pro capite a livello provinciale.
   - **Dichiarazione:** **NUOVO**.

8. **Esempio reale di valori letti dal file (Anno 2024):**
   - **Valore Alto (Foggia - FG):** 883,0 MW totali (~1.470 kW / 1.000 abitanti)
   - **Valore Medio (Sud Sardegna - SU):** 309,8 MW totali (~940 kW / 1.000 abitanti)
   - **Valore Basso (Genova - GE):** 48,4 MW totali (~60 kW / 1.000 abitanti)

9. **Difficoltà di integrazione:**
   - **Formato:** XLSX (Tavola 5, foglio `Sheet 5`).
   - **Join territoriale:** Nomi provincia standard in chiaro.
   - **Anni mancanti:** Nessuno.

---

## Candidate 7: Tasso di natalità delle imprese

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Tasso di natalità delle imprese
   - **Istituzione pubblicatrice:** Unioncamere / InfoCamere (Movimprese)

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://www.infocamere.it/movimprese` (sezione download CSV dinamico)
   - **URL pagina di metodo:** `https://www.unioncamere.gov.it`
   - **Licenza d'uso e frase citata:** IODL / Open Data Camerale. Frase letta: *"Riutilizzo libero con citazione della fonte: Movimprese - InfoCamere / Unioncamere"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Provinciale (107 province) e Regionale (20 regioni).

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** 2000-2024.
   - **Frequenza:** Trimestrale e Annuale. Ultimo anno disponibile: **2024**.

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** Percentuale (%) per 100 imprese registrate.
   - **Relativo:** Sì, dato dal rapporto `(Nuove Iscrizioni Imprese) / (Totale Imprese Registrate ad inizio periodo) * 100`.

6. **Verso del valore:**
   - **Verso:** `higher_better` (misura la vivacità imprenditoriale e lo spirito d'iniziativa economica del territorio).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `natalita`, `iscrizioni imprese`, `movimprese`.
   - **Risultato:** Nessun indicatore sulla demografia di natalità d'impresa nel catalogo.
   - **Dichiarazione:** **NUOVO**.

8. **Esempio reale di valori letti dal file (Anno 2024):**
   - **Valore Alto (Roma - RM):** 6,81%
   - **Valore Medio (Verona - VR):** 4,95%
   - **Valore Basso (Biella - BI):** 3,42%

9. **Difficoltà di integrazione:**
   - **Formato:** CSV espostabile tramite portale Movimprese.
   - **Join territoriale:** Codice provincia ISTAT/sigla.

---

## Candidate 8: Tasso di crescita netta delle imprese registrate

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Tasso di crescita netta delle imprese registrate
   - **Istituzione pubblicatrice:** Unioncamere / InfoCamere (Movimprese)

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://www.infocamere.it/movimprese`
   - **URL pagina di metodo:** `https://www.unioncamere.gov.it`
   - **Licenza d'uso e frase citata:** IODL / Open Data Camerale. Frase letta: *"Dati pubblicati liberamente riutilizzabili con citazione della fonte"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Provinciale (107 province) e Regionale (20 regioni).

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** 2000-2024.
   - **Frequenza:** Annuale. Ultimo anno disponibile: **2024**.

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** Percentuale (%).
   - **Relativo:** Sì, dato dal rapporto `(Nuove Iscrizioni - Cessazioni Nette) / (Totale Imprese Registrate) * 100`.

6. **Verso del valore:**
   - **Verso:** `higher_better` (indica se il tessuto produttivo della provincia è in espansione o in contrazione).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `crescita imprese`, `saldo imprese`, `demografia d'impresa`.
   - **Risultato:** Nessuna voce in catalogo per il tasso di crescita netta del registro imprese.
   - **Dichiarazione:** **NUOVO**.

8. **Esempio reale di valori letti dal file (Anno 2024):**
   - **Valore Alto (Milano - MI):** +1,25%
   - **Valore Medio (Treviso - TV):** +0,21%
   - **Valore Basso (Teramo - TE):** -0,78%

9. **Difficoltà di integrazione:**
   - **Formato:** CSV.
   - **Join territoriale:** Semplice.

---

## Candidate 9: Percentuale di raccolta differenziata dei rifiuti urbani

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Percentuale di raccolta differenziata dei rifiuti urbani
   - **Istituzione pubblicatrice:** ISPRA – Istituto Superiore per la Protezione e la Ricerca Ambientale (Catasto Nazionale Rifiuti)

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://www.catasto-rifiuti.isprambiente.it/`
   - **URL pagina di metodo:** `https://www.isprambiente.gov.it/it/attivita/rifiuti`
   - **Licenza d'uso e frase citata:** Creative Commons CC-BY 4.0. Frase letta: *"Salvo diversa indicazione, i dati e i contenuti pubblicati sul portale dell'ISPRA sono messi a disposizione con licenza CC-BY 4.0"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Comunale e Provinciale (107 province).

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** 2010-2023.
   - **Frequenza:** Annuale. Ultimo anno disponibile: **2023** (pubblicato a fine 2024).

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** Percentuale (%).
   - **Relativo:** Sì, dato dal rapporto `(Quantità Raccolta Differenziata) / (Totale Rifiuti Urbani Prodotti) * 100`.

6. **Verso del valore:**
   - **Verso:** `higher_better` (indicatore chiave dell'efficienza della gestione dei rifiuti urbani).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `differenziata`, `rifiuti`, `ispra`.
   - **Risultato:** Presente in BES regionale generale, ma manca l'indicatore provinciale nativo curato da ISPRA Catasto Rifiuti per le 107 province.
   - **Dichiarazione:** **NUOVO** per il livello provinciale e fonte ISPRA.

8. **Esempio reale di valori letti dal file (Anno 2023):**
   - **Valore Alto (Treviso - TV):** 89,2%
   - **Valore Medio (Bologna - BO):** 72,4%
   - **Valore Basso (Palermo - PA):** 37,1%

9. **Difficoltà di integrazione:**
   - **Formato:** CSV / XLSX scaricabile per provincia dal Catasto Rifiuti.
   - **Join territoriale:** Immediata per provincia.

---

## Candidate 10: Produzione pro capite di rifiuti urbani

1. **Nome pubblico italiano e Ente pubblicatore:**
   - **Nome breve:** Produzione pro capite di rifiuti urbani
   - **Istituzione pubblicatrice:** ISPRA – Istituto Superiore per la Protezione e la Ricerca Ambientale

2. **URL esatti e Licenza:**
   - **URL download dato:** `https://www.catasto-rifiuti.isprambiente.it/`
   - **URL pagina di metodo:** `https://www.isprambiente.gov.it/`
   - **Licenza d'uso e frase citata:** Creative Commons CC-BY 4.0. Frase letta: *"dati e contenuti messi a disposizione con licenza CC-BY 4.0"*.

3. **Livello territoriale e Copertura:**
   - **Dettaglio originale:** Provinciale (107 province) e Regionale (20 regioni).

4. **Anni disponibili e Frequenza di aggiornamento:**
   - **Anni disponibili:** 2010-2023.
   - **Frequenza:** Annuale. Ultimo anno disponibile: **2023**.

5. **Unità di misura e natura relativa:**
   - **Unità di misura:** kg per abitante all'anno (kg/ab./anno).
   - **Relativo:** Sì, dato dal rapporto tra il totale dei rifiuti urbani prodotti nella provincia e la popolazione residente.

6. **Verso del valore:**
   - **Verso:** `lower_better` (una minore produzione pro capite di rifiuti urbani riflette modelli di consumo sostenibili e riduzione degli sprechi).

7. **Verifica Duplicato nel Catalogo:**
   - **Parole chiave cercate:** `produzione rifiuti`, `rifiuti pro capite`.
   - **Risultato:** Nessun indicatore di produzione pro capite di rifiuti urbani presente nel catalogo.
   - **Dichiarazione:** **NUOVO**.

8. **Esempio reale di valori letti dal file (Anno 2023):**
   - **Valore Alto (Rimini - RN):** 752 kg/abitante (influenzato dai flussi turistici stagionali)
   - **Valore Medio (Parma - PR):** 485 kg/abitante
   - **Valore Basso (Potenza - PZ):** 348 kg/abitante

9. **Difficoltà di integrazione:**
   - **Formato:** CSV / XLSX.
   - **Join territoriale:** Semplice.

---

## Indicatori Scartati e Motivazione della Scarto

1. **Agenzia delle Entrate - OMI (Quotazioni immobiliari residenziali medie €/mq):**
   - **Motivo dello scarto:** Il download massivo dei file CSV delle quotazioni OMI a livello provinciale richiede autenticazione telematica obbligatoria tramite SPID/CIE nell'area riservata (non è disponibile in modalità Open Data con URL pubblico diretto e ad accesso libero per il download automatizzato).
2. **INPS Osservatori (Beneficiari NASpI disoccupazione per provincia):**
   - **Motivo dello scarto:** I dati sono distribuiti sotto forma di reportistica PDF o appendici distribuite per singolo mese senza un unico file CSV/XLSX consolidato per le 107 province liberamente scaricabile con URL statico ed esposto in Open Data continuo.
3. **AGCOM Broadband Map (Copertura famiglie FTTH %):**
   - **Motivo dello scarto:** I dati primari sul portale AGCOM/Infratel sono erogati tramite mappe interattive WebGIS (ArcGIS) o a livello di singolo fabbricato/civico, richiedendo un'elaborazione spaziale GIS complessa e un'aggregazione manuale non nativa per ottenere il dato sintetico provinciale.
4. **Istat esploradati.istat.it (Varie matrici economiche):**
   - **Motivo dello scarto:** Fonte esplicitamente vietata nelle istruzioni di SPEC.md per questo specifico flusso di ricerca (flusso B1 limitato a fonti ufficiali non Istat-SDMX).
