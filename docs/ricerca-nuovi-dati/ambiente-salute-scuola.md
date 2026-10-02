# Ricerca indicatori nuovi, flusso B2 (fonti non Istat-SDMX)

Data: 1 ottobre 2026. Solo ricerca, nessuna modifica al codice. Le sezioni sotto sono i rapporti dettagliati per area (in `parti/`, con i file scaricati in `parti/fonti_*`); ogni scheda ha i 9 punti richiesti. Elenco dei nomi in catalogo usato per i doppioni: `parti/catalogo_nomi.txt`.

## Sintesi ordinata per valore

Priorità alta (facili, relativi, ultimo anno >= 2023, copertura completa):
1. ISPRA, quota di aree a pericolosità idraulica già consumate (S1): 107 province, 20 regioni, 2006-2024, CC BY 4.0 IT.
2. ISPRA IdroGEO, % territorio a pericolosità da frana elevata P3+P4 e % a pericolosità idraulica media: 107 province, API JSON (licenza da riconfermare).
3. ISPRA, territorio alterato dal consumo di suolo, fascia 100 m (S3): 107 province, 20 regioni, 2006-2024.
4. Ministero dell'Istruzione e del Merito, alunni della primaria a tempo pieno; alunni per classe; docenti supplenti: 104 province, 18 regioni (mancano Aosta, Bolzano, Trento), IODL 2.0.
5. Ministero dell'Economia e delle Finanze, reddito imponibile IRPEF medio per contribuente e % contribuenti oltre 55.000 euro: 107 province da CSV comunale 2024 (CC BY 3.0 IT, frase non letta).
6. Ministero della Salute, copertura antinfluenzale 65+ (regioni, 2024-25) e farmacie per 10.000 abitanti (107 province, IODL 2.0, Sardegna da rimappare).
7. ISPRA, nuovo consumo di suolo per ettaro (S5).
8. Ministero dell'Università e della Ricerca, iscritti che studiano fuori regione (20 regioni).

Priorità media: copertura vaccinale a 24 mesi (solo PDF), autovetture per 100 abitanti (ACI, contextual), edifici con palestra (autodichiarato), potenza fotovoltaica per abitante e consumi elettrici domestici per abitante (da PDF, serve la popolazione), % SAU biologica (solo regioni, serve la SAU), suolo consumato entro 300 m dalla costa, quota di aree franose consumate (S2, copertura parziale).

Priorità bassa o in attesa: isola di calore urbana (un solo anno), NO2 (provvisorio, per stazione), screening oncologici ISS (licenza non trovata), detenuti su capienza (licenza "non commerciale"), suolo pro capite (derivato).

Non coperto, perché non raggiunto o non verificato: delitti denunciati per provincia (Ministero dell'Interno: server in timeout), musei e visitatori (doppione e assoluti), presenze turistiche (solo via esploradati, escluso), AGENAS, ARERA, AGCOM, MIMIT, MASE, Protezione Civile, OMI.

Attenzioni trasversali: (a) nessun candidato è un assoluto, salvo i due da PDF Terna/GSE e SINAB che vanno divisi per popolazione o SAU (dichiarato in scheda); (b) tre schede hanno la licenza dedotta e non letta: Terna, GSE, SINAB, MEF, ISS, IdroGEO; va riconfermata prima di integrare; (c) l'URL del file completo ISPRA `consumo_suolo_full_v1.1.xlsx` non è stato ricostruito; (d) le schede salute, scuola, sicurezza e ambiente sono state istruite da subagent e aprono le fonti con curl; i valori d'esempio sono quelli letti dal file, ricontrollati a campione solo per la parte ISPRA suolo.

---

## ISPRA, consumo di suolo 2025 (dati 2006-2024)

Fonte comune a tutti i candidati di questa sezione.

- Istituzione: Istituto Superiore per la Protezione e la Ricerca Ambientale (ISPRA), con il Sistema Nazionale per la Protezione dell'Ambiente (SNPA).
- Pagina dati: https://www.isprambiente.gov.it/it/attivita/suolo-e-territorio/suolo/il-consumo-di-suolo/i-dati-sul-consumo-di-suolo (aperta, 1/10/2026).
- Estratto scaricabile (solo incrementi in ettari + suolo consumato 2024, fogli Comuni/Province/Regioni): https://www.isprambiente.gov.it/it/attivita/suolo-e-territorio/suolo/il-consumo-di-suolo/consumo_di_suolo_estratto_dati_2025_anni_2006_2024.xlsx
- File completo `consumo_suolo_full_v1.1.xlsx` (63 MB, fogli `Comuni_AAAA`, `Province_AAAA`, `Regioni_AAAA`, `Nazionale_AAAA` per AAAA = 2006, 2012, 2015-2024, più `_2023_rev`; foglio `Descrizione_campi` con 100 campi): letto da copia locale scaricata da un worker precedente. **L'URL esatto di questo file non l'ho ricostruito dalla pagina (non compare tra i link): non verificato.** Va richiesto/ritrovato dal sito consumosuolo.isprambiente.it prima di integrare.
- Sintesi: https://www.snpambiente.it/wp-content/uploads/2025/10/sintesi-consumo-di-suolo-2025.pdf ; schede regionali: https://www.snpambiente.it/wp-content/uploads/2025/10/SCHEDE_REGIONALI_2025.pdf
- Licenza: la sintesi riporta "Dati e cartografia (in licenza CC BY 4.0 IT)".
- Territori: foglio Province con 107 righe (nome provincia + `cod_prov` ISTAT numerico, es. 1 = Torino); foglio Regioni con 20 righe, Trentino-Alto Adige già aggregato (Bolzano e Trento sono due province distinte nel foglio Province). Join per codice ISTAT provincia/regione, i nomi hanno apostrofi diversi ("Forli'-Cesena").
- Anni: 2006, 2012, 2015, 2016, ..., 2024 (annuale dal 2015); ultimo 2024, uscita annuale (rapporto SNPA a ottobre).
- Errore possibile: nel foglio `Descrizione_campi` le etichette di `nome_regione` e `nome_provincia` sono scambiate (righe 4 e 6). Le colonne dati sono corrette.

Esempio di lettura (2024, provincia): Torino suolo consumato 8,60 %; Aosta 2,16 %; Monza e della Brianza 40,92 %.

### Doppione già nel catalogo

`10AMB018P` "Impermeabilizzazione del suolo da copertura artificiale" (BES dei Territori, % , lower_better, 107 province, 2015-2023). È la stessa misura di `csuolo4` (suolo consumato %): **non riproporre la % di suolo consumato**. Anche "Erosione dello spazio rurale da dispersione urbana" è già in catalogo (non confrontato campo per campo: dichiarato probabile doppione di `formet5`, da verificare).

### Candidati NUOVI da questo file

**S1. Suolo consumato in aree a pericolosità idraulica media** (campo `pidrau3`, anche `pidrau6` bassa e `pidrau9` alta)
- Nome pubblico: "Quota di aree a pericolosità idraulica già consumate"; ISPRA.
- Definizione verificata: `pidrau3` = `pidrau1 / (pidrau1 + pidrau2) * 100` (ricalcolato per Torino 12,72, Napoli 33,98, Bolzano 18,46, Roma 22,30: coincide), cioè la % della superficie in classe di pericolosità 1 (la più alta delle tre, da confermare sulla legenda del rapporto: non verificato) già coperta da suolo consumato.
- Livello: 107 province su 107; 20 regioni. Anni 2006-2024 (stessa mappa di pericolosità, cambia il consumato).
- Unità: %; relativo. Verso: lower_better (più area esposta già cementificata = più esposizione). Onesto.
- Doppione: il catalogo ha "Popolazione esposta al rischio di alluvioni" (persone esposte), misura diversa (popolazione, non superficie consumata). Nuovo.
- Esempio 2024 province: Trieste 58,19 % (alto), Matera 2,32 % (basso), Cagliari 11,34 % (medio). Regioni: Liguria 33,29 %, Basilicata 2,62 %, Lombardia 11,00 %.
- Integrazione: facile (foglio per anno, stesse colonne). Attenzione: pidrau9 ha 105 province valide (Bolzano 0).

**S2. Suolo consumato in aree a pericolosità da frana** (campi `pfrane11`-`pfrane15`)
- Nome: "Quota di aree franose già consumate". ISPRA. % relativa, lower_better.
- Copertura incompleta: `pfrane13` 100 province, `pfrane14` 101, `pfrane15` solo 43. Regioni: 20 per 13 e 14. L'etichetta delle classi 1-5 (P1-P4 + aree di attenzione?) non è verificata: serve il rapporto completo.
- Esempio 2024 (`pfrane14`, province): Barletta-Andria-Trani 22,26 % (alto), Aosta 0,40 % (basso), Messina 2,98 % (medio). Regioni: Umbria 7,13 %, Valle d'Aosta 0,40 %, Marche 2,67 %.
- Difficoltà: media (scegliere la classe; 6-13 province senza valore).
- Doppione: "Popolazione esposta al rischio di frane" è in catalogo, misura diversa. Nuovo.

**S3. Suolo alterato (frammentazione ecologica)** (campi `diseco3` 60 m, `diseco6` 100 m, `diseco9` 200 m)
- Nome: "Territorio alterato dal consumo di suolo (fascia di 100 m)". ISPRA. % relativa. lower_better.
- 107 province, 20 regioni, 2006-2024. Non è la % di suolo consumato: misura l'effetto di bordo (distanza dalle superfici artificiali).
- Esempio 2024 `diseco6` province: Monza e della Brianza 91,67 % (alto), Aosta 17,37 % (basso), Forlì-Cesena 49,69 % (medio). Regioni `diseco3`: Puglia 45,06 %, Valle d'Aosta 12,21 %, Friuli-Venezia Giulia 32,70 %.
- Quasi collineare con `csuolo4` ma il rango cambia (Puglia ultima per alterazione, non per consumo). Doppione: nessuno, nel catalogo non c'è una misura di frammentazione. Nuovo.
- Difficoltà: bassa.

**S4. Isola di calore urbana** (campo `iscalo1`, °C di differenza urbano-rurale)
- Nome: "Isola di calore urbana (differenza di temperatura estiva)". ISPRA. Unità: °C (differenza, relativa). lower_better.
- Solo 2024 (foglio `Province_2024`: 107 valori; `Regioni_2024`: 20). Un solo anno: non fa serie. Valori negativi possibili (Trapani -2,66 °C).
- Esempio province: Trento 14,86 °C (alto), Trapani -2,66 °C (basso), Reggio di Calabria 7,19 °C (medio). Regioni: Lombardia 12,19 °C, Puglia 0,44 °C, Toscana 8,03 °C.
- Doppione: nessuno. Nuovo ma 1 anno solo: priorità bassa. Il metodo di calcolo dell'indicatore non è stato verificato (solo il nome campo).

**S5. Incremento annuo di suolo consumato per ettaro** (campo `csuolo9`, m²/ha)
- Nome: "Nuovo consumo di suolo (m² per ettaro)". ISPRA. Relativo alla superficie provinciale. lower_better. Valore annuale, volatile (tra 2023 e 2024 Italia 2,78 m²/ha).
- 107 province, 20 regioni, annuale 2012-2024 (le righe 2012 e 2015 sono periodi pluriennali: 2006-12, 2012-15).
- Esempio 2024 province: Cagliari 17,78 (alto), Imperia 0,11 (basso), Biella 1,94 (medio). Regioni: Lazio 4,57, Valle d'Aosta 0,33, Friuli-Venezia Giulia 2,30.
- Doppione: nessuna misura di flusso in catalogo (solo stock). Nuovo. Il dato 2023 ha una versione `_rev` da non mescolare con le uscite precedenti.

**S6. Suolo consumato entro 300 m dalla costa** (campo `ccoste8`)
- % della fascia 0-300 m già consumata. ISPRA. 60 province costiere su 107; 15 regioni (le sole con costa). Verso lower_better. Esempio 2024: Forlì-Cesena 65,24 % (alto), Padova 0,44 % (basso), Messina 29,82 % (medio); regioni: Liguria 48,17 %, Basilicata 6,98 %, Calabria 29,63 %.
- Copertura territoriale parziale per costruzione: non si può calcolare un punteggio di tema alla pari con le altre misure. Candidato debole per l'atlante, utile per un articolo.

**S7. Suolo consumato per abitante** (m²/ab; non è un campo del file)
- La sintesi (pag. 5-6) riporta il valore nazionale 365,8 m²/ab nel 2024 (347 nel 2006). Il valore provinciale si ricava dividendo `csuolo1` (ettari) per la popolazione residente: richiede la popolazione Istat per provincia, già presente nel sito. Il file contiene `clammi4` ("POP_") ma non è documentato l'anno: non usarlo.
- Misura diversa dalla % (pro capite premia i territori con bassa densità); verso lower_better. Nuovo in catalogo. Integrazione: calcolo derivato (da dichiarare in metodo), non un dato scaricabile diretto.

### Scartati da questo file
- `csuolo4` (% suolo consumato): doppione di 10AMB018P.
- `csuolo1` e tutti i campi in ettari (`csuolo8`, `csuolo10`, `csuolo11`, `csuolo12`, `csuolo13`, `careep*`, `ccoste1-7`, `caltim*` in ha): assoluti, premiano la taglia.
- `caltim*`, `careep2`/`vinpae1` (quota in aree protette): non verificata la conversione in % utile; `vinpae` richiede di capire il denominatore. `formet5` (indice di dispersione): probabile doppione di "Erosione dello spazio rurale da dispersione urbana" già in catalogo.
- `clammi*` (zona altimetrica, TA, POP): descrittori, non indicatori.

---

# Ricerca ambiente ed energia: candidati nuovi (1 ottobre 2026)

Sola ricerca, nessuna modifica al codice. File scaricati in `lavoro/parti/fonti_ambiente/`.
Il catalogo di confronto e `lavoro/parti/catalogo_nomi.txt` (grep per parola chiave fatto su: rifiut, differenzi, aria, no2, ozono, fotovolt, rinnovabil, biolog, elettric, consumi, siti, contamin, protett, frane, alluvion, idrogeo, verde, suolo).

Ogni dato qui sotto e stato letto da un file aperto davvero. Dove no, c'e scritto "non verificato".
Nota tecnica: sinab.it ha la catena di certificati incompleta (curl fallisce senza `-k`); i file SINAB sono stati scaricati con `-k`, sono pubblici e a sola lettura.

## Sintesi (priorita)

| # | Candidato | Fonte | Livello | Ultimo anno | Verso | Difficolta |
|---|-----------|-------|---------|-------------|-------|-----------|
| 1 | Territorio a pericolosita da frana elevata e molto elevata (%) | ISPRA IdroGEO | 107 province, 20 regioni | ed. 2024 | lower_better | bassa (API JSON) |
| 2 | Territorio a pericolosita idraulica media (%) | ISPRA IdroGEO | 107 province, 20 regioni | ed. 2024 | lower_better | bassa (stessa API) |
| 3 | Biossido di azoto, media annua (ug/m3) | ISPRA/SNPA (ISQA) | ~104 province su 107 | 2024 (provvisorio) | lower_better | media (stazioni da aggregare) |
| 4 | Potenza fotovoltaica installata per abitante | GSE | 107 province | 31/12/2024 | contextual | media (tabella in PDF + popolazione) |
| 5 | Consumi elettrici domestici per abitante | Terna | 107 province | 2024 (con 2023) | contextual | media (tabella in PDF + popolazione) |
| 6 | Superficie agricola biologica sul totale (%) | SINAB / MASAF | 20 regioni | 2024 | higher_better | media (PDF, denominatore a parte) |
| riserva | Ozono: giorni di superamento obiettivo a lungo termine | ISPRA/SNPA (ISQA) | ~province con stazioni | 2024 (provvisorio) | lower_better | media |
| riserva | Rifiuti speciali prodotti per abitante | ISPRA Catasto Rifiuti | 20 regioni | 2023 | contextual | media (assoluti in t) |

Raccomandazione netta: fare subito 1 e 2 (dato pulito, API, 107 province, nessun doppione); poi 4 e 5 (utili ma obbligano a un join con la popolazione e a leggere PDF); 3 solo dichiarando che e provvisorio e che e una media di stazioni; 6 solo regionale. Non fare ancora: ozono, rifiuti speciali, rifiuti indifferenziati (vedi sotto).

---

## 1 e 2. Pericolosita idrogeologica: % di territorio (ISPRA IdroGEO)

1. Nome: "Territorio a pericolosita da frana elevata e molto elevata (P3+P4)" e "Territorio a pericolosita idraulica media (P2)". Istituzione: ISPRA, Istituto superiore per la protezione e la ricerca ambientale, piattaforma IdroGEO.
2. Dato scaricabile (API pubblica, JSON): `https://idrogeo.isprambiente.it/api/pir/province` (elenco 107 province con codici) e `https://idrogeo.isprambiente.it/api/pir/province/<uid>` (un record per provincia, 1..107); regioni `https://idrogeo.isprambiente.it/api/pir/regioni` e `.../regioni/<uid>`. Pagina dei dati aperti: `https://idrogeo.isprambiente.it/app/page/open-data` (e un'app JavaScript, il testo non e leggibile con curl). Metodo: Rapporto ISPRA 415/2025 "Dissesto idrogeologico in Italia: pericolosita e indicatori di rischio. Edizione 2024", `https://www.isprambiente.gov.it/files2025/pubblicazioni/rapporti/rapporto_ispra_dissesto_idrogeologico_ed2024_web.pdf` (scaricato, 220 pagine).
   Licenza: la frase "CC BY 4.0" per IdroGEO l'ho trovata solo nel riassunto di una ricerca web, NON letta sulla pagina (app JS) ne nel rapporto. Il rapporto dice (p. 159) che la pagina Open data permette di scaricare "indicatori di rischio su base nazionale, regionale, provinciale e comunale". Per il sito ISPRA vale la frase letta in `https://www.isprambiente.gov.it/it/note-legali`: "Salvo ove diversamente indicato, i dati pubblicati sul presente sito sono messi a disposizione con licenza CC-BY 4.0". Quindi: licenza probabile CC BY 4.0, da confermare a mano sulla pagina Open data.
3. Livello: province, 107 su 107 (uid 1..107, codici in `cod_reg`, `cod_prov`; include Sud Sardegna, Monza, Fermo, BAT, Bolzano, Trento separate). Regioni: 20 (Trentino-Alto Adige come regione unica nell'elenco; Bolzano e Trento sono due province, quindi la TAA si somma da loro). Esiste anche il livello comunale.
4. Anni: mosaicatura PAI v5.0 del 2024 (nel rapporto: confronto con quella 2020-2021), popolazione e edifici dal Censimento 2021. Edizioni triennali circa (2015, 2018, 2021, 2024): non e una serie annuale, e le classi cambiano con gli aggiornamenti dei PAI. Ultimo 2024, ok per il vincolo >= 2023. Serie storica comparabile: non verificata.
5. Unita: percentuale di superficie provinciale (campi `ar_frp3p4p`, `aridp2_p`, `aridp3_p`; sono anche presenti `ar_kmq` e i km2 assoluti). Relativo, ok.
6. Verso: lower_better (piu territorio a pericolosita elevata = peggio per esposizione). Si puo discutere "contextual" perche la pericolosita e geografia, non politica.
7. Doppione: nuovo. In catalogo ci sono "Popolazione esposta a rischio frane/alluvione", "Densita popolazione a rischio frane": misurano popolazione, non territorio. Nessun nome con "% di territorio" o "pericolosita".
8. Esempio (letto da `idrogeo_province_pir.json`, ed. 2024, % del territorio provinciale a pericolosita frana P3+P4): alto Aosta 83,7; medio (posizione 54 su 107) Verbano-Cusio-Ossola 6,6; basso Cremona 0,0. Per la pericolosita idraulica media P2: alto Ferrara 99,9; medio Matera 6,8; basso Palermo 0,6. Nota: le province con PAI non aggiornati o senza mappatura danno zeri che non vogliono dire sicurezza.
9. Integrazione: facile, 107 chiamate GET; il join e per `cod_prov` (verificare i codici contro quelli del sito, Sardegna e il punto fragile). Rischio: il 100% di Ferrara (pianura bonificata) schiaccia la scala, serve una nota di metodo. Il file `idrogeo_main.js` e i chunk non contengono l'indirizzo CSV; usare l'API.

## 3 (e riserva). Qualita dell'aria: NO2 e ozono (ISPRA/SNPA, tabelle ISQA)

1. Nome: "Biossido di azoto (NO2), media annua" e "Ozono, giorni di superamento dell'obiettivo a lungo termine". Istituzione: SNPA, Sistema nazionale per la protezione dell'ambiente, con ISPRA e le ARPA.
2. File: `https://www.snpambiente.it/wp-content/uploads/2025/03/20250307_2024_NO2_TABELLA_ISQA.csv` (e `.xlsx`), `https://www.snpambiente.it/wp-content/uploads/2025/03/20250218_2024_O3_TABELLA_ISQA.csv`. Pagine: `https://www.snpambiente.it/no2-la-situazione-nel-2024/`, `https://www.snpambiente.it/ozono-la-situazione-nel-2024/`. Metodo: le pagine citate e l'indicatore ISPRA `indicatoriambientali.isprambiente.it` (non letto a fondo). Licenza: nessuna frase trovata sulle pagine SNPA; non verificata.
3. Livello: stazione di misura, con colonne regione, provincia, comune. Ho aggregato per provincia: 104 province con almeno una stazione NO2 valida (mancano, per nome, almeno Crotone, Fermo, Vibo Valentia; gli altri scarti nel confronto con IdroGEO sono solo nomi scritti diversi). Province ex Friuli e liberi consorzi siciliani hanno etichette diverse.
4. Anni: 2024, file elaborato dalle ARPA subito a fine anno; il file stesso dice che la validazione "in alcuni casi non e ancora arrivata all'ultimo stadio". Serie: ogni anno ha il suo file (non scaricati gli anni precedenti, non verificato); annuale.
5. Unita: ug/m3 (NO2); giorni (ozono). Relativo.
6. Verso: lower_better.
7. Doppione: nuovo. In catalogo ci sono "Qualita dell'aria - PM2.5" e "Monitoraggio della qualita dell'aria", non NO2 ne ozono.
8. Esempio NO2 2024, media delle stazioni della provincia (calcolata da me sul file): alto Milano 30,3; medio Cuneo 15,6; basso Sud Sardegna 3,7 ug/m3. Il valore alto e un'effettiva media di stazioni di traffico e fondo mischiate.
9. Integrazione: media; l'indicatore dipende da come si aggregano stazioni di tipo diverso (traffico, fondo, rurale): servirebbe una regola dichiarata (per esempio solo fondo urbano) e il dato provvisorio va etichettato. Il valore medio di una provincia con una sola stazione rurale non e confrontabile con Milano. Per questo e il candidato piu debole dei sei.

## 4. Potenza fotovoltaica per abitante (GSE)

1. Nome: "Potenza fotovoltaica installata per abitante". Istituzione: GSE, Gestore dei servizi energetici.
2. File: `https://www.gse.it/documenti_site/Documenti%20GSE/Rapporti%20statistici/Solare%20Fotovoltaico%20-%20Rapporto%20Statistico%202024.pdf` (scaricato; tabella 9 "Numerosita e potenza degli impianti fotovoltaici per provincia a fine 2024", p. 13). Metodo: stesso rapporto. Pagina: `https://www.gse.it/dati-e-scenari/statistiche`. Licenza: il sito GSE non l'ho potuto leggere (pagine JS, `gse.it/note-legali` da 404, `opendata.gse.it` da errore certificato). Una ricerca web riporta "CC BY 3.0 IT" per i dati GSE, solo da risultato di ricerca: non verificato.
3. Livello: 107 province (tabella a due colonne: Sud Sardegna, BAT, Fermo, Monza ecc. presenti; Bolzano e Trento separate) piu totale Italia 1.875.870 impianti e 37.002 MW.
4. Anni: fine 2024; rapporti annuali precedenti esistono (2022, 2023 sullo stesso indirizzo, non scaricati). Frequenza annuale.
5. Unita: MW e numero impianti (assoluti). Serve dividere per la popolazione residente per averlo relativo (kW per abitante).
6. Verso: contextual (piu diffusione = piu rinnovabile, ma pesa la vocazione agricola e il terreno; higher_better e difendibile solo come "diffusione").
7. Doppione: parziale. In catalogo "Potenza efficiente lorda delle fonti rinnovabili", "Energia prodotta da fonti rinnovabili", "Energia elettrica da fonti rinnovabili": regionali e di fonte Terna/Istat, tutte fonti rinnovabili insieme, non il solo fotovoltaico, non provinciali. Il fotovoltaico per provincia e nuovo; controllare solo che "Potenza efficiente lorda" non sia gia per provincia.
8. Esempio (tabella 9, potenza a fine 2024): alto Viterbo 1.580 MW; medio Ancona 414 MW; basso Aosta 40 MW. Sono assoluti: il relativo richiede la popolazione.
9. Integrazione: media-alta; il PDF va estratto in tabella (ho estratto il testo con pypdf, la tabella e leggibile ma a due blocchi per riga). Verificare se Atlaimpianti o `opendata.gse.it` danno un CSV: non verificato.

## 5. Consumi elettrici domestici per abitante (Terna)

1. Nome: "Consumi elettrici delle famiglie per abitante". Istituzione: Terna S.p.A., gestore della rete di trasmissione.
2. File: `https://download.terna.it/terna/06_CONSUMI_8de38d06c930a94.pdf` (scaricato; tabella 45 "Consumi di energia elettrica in Italia secondo settore di utilizzazione e provincia", pp. 23-26, GWh per Agricoltura, Industria, Servizi, Domestico, Totale, anni 2023 e 2024). Metodo: note `https://download.terna.it/terna/Nota_metodologica_8da42531c0ff392.pdf` (indirizzo letto sulla pagina Terna, non aperto). Pagina: `https://www.terna.it/it/sistema-elettrico/statistiche/pubblicazioni/consumi-energia-elettrica`; portale `https://dati.terna.it/en/load/statistical-data` (dice che i dati provinciali si esportano dal "Download Center", nessun URL fisso). Licenza: nessuna frase trovata, non verificata.
3. Livello: 107 province, tutte presenti (anche Sud Sardegna, BAT, Fermo, Monza; Bolzano e Trento separate), piu regioni e Italia. Valle d'Aosta e Aosta coincidono.
4. Anni: 2023 e 2024 nel file; gli annuari precedenti (2018, 2021, 2022, 2023) hanno lo stesso schema su download.terna.it, non scaricati. Annuale.
5. Unita: GWh (assoluti). Per l'indicatore: GWh domestici diviso per popolazione, kWh/abitante. Il totale a livello provincia pesa troppo l'industria (Taranto, Siracusa): usare solo domestico o servizi.
6. Verso: contextual.
7. Doppione: no. In catalogo ci sono i consumi di energia elettrica di PA per ULA, imprese di agricoltura, industria, terziario, illuminazione pubblica: nessuno e domestico ne per abitante. Controllare che il consumo domestico non sia gia presente con altro nome (cercato "domestic": nessun risultato).
8. Esempio (domestico 2024, GWh): alto Roma 4.692,0; intermedio Catania 1.216,3 (valore intermedio scelto a occhio, mediana non calcolata); basso Enna 152,1 (colonna Domestico, 2024). Assoluti, non confrontabili senza popolazione.
9. Integrazione: media. Il PDF ha spazi spuri dentro i numeri ("6 07,3", "2.6 97,5", "1.0 87,0") che rompono un parsing ingenuo; serve normalizzazione o un controllo che la somma delle colonne torni col totale. Dal portale Terna si potrebbe ottenere un CSV: non verificato.

## 6. Superficie agricola biologica (SINAB)

1. Nome: "Superficie biologica sulla superficie agricola utilizzata (%)". Istituzione: SINAB, Sistema d'informazione nazionale sull'agricoltura biologica, per il MASAF (Ministero dell'agricoltura).
2. File: `https://sinab.it/wp-content/uploads/2025/12/Rapporto-BIC-ISMEA-2025-web_17_12.pdf` (scaricato, 112 pagine; "Bio in cifre 2025", dati 2024). Tabella 1.5 (p. 24) "Distribuzione territoriale delle superfici biologiche in Italia (ha)", anni 2015, 2023, 2024, per regione; Tabella 2.3 operatori per regione. Pagina: `https://sinab.it/bionovita/bio-in-cifre-2025-il-rapporto-completo/`. Licenza: nessuna frase trovata; non verificata.
3. Livello: 20 regioni, con Bolzano e Trento separate (si sommano per la TAA). Province: NON disponibili in questo rapporto (le province compaiono solo per la vite).
4. Anni: 2015, 2023, 2024 nel file; serie annuale nel resto della collana (non scaricata). Nota di rottura: Valle d'Aosta passa da 2.000 ha (2023) a 37.087 ha (2024), il rapporto lo mostra (+1.753,9%): serve una nota o una soglia.
5. Unita: ettari (assoluti). Il rapporto da l'incidenza % sulla SAU totale solo come grafico (Grafico 1.9, 8 regioni sopra il 25%): nel testo estratto i valori non hanno etichetta di regione. Per il relativo serve la SAU totale regionale (7 Censimento agricoltura), da prendere altrove. Totale Italia 20,2% della SAU letto nel testo.
6. Verso: higher_better.
7. Doppione: nuovo (grep "biolog": nessun risultato).
8. Esempio (Tabella 1.5, ha biologici 2024): alto Sicilia 402.779; medio Veneto 41.052; basso Liguria 9.548. Assoluti.
9. Integrazione: media-alta; PDF, solo 20 regioni, denominatore da un'altra fonte. Se la SAU e gia in catalogo, la parte facile e fare il rapporto. Gli operatori biologici per provincia (richiesti) non li ho trovati: scartati (vedi sotto).

---

## Riserve non consigliate ora

- Rifiuti speciali prodotti: `https://www.catasto-rifiuti.isprambiente.it/speciali/getProduzioneRSRegione.csv.php?pg=prodrsnazione&aa=2023&regid=` (CSV scaricato, 20 regioni piu Italia, anno 2023, tonnellate: Lombardia 35.894.407, Piemonte 13.722.294, Valle d'Aosta 303.123). Assoluti, dominati da industria e costruzioni: per abitante non e un giudizio sulla gestione. Nuovo nel catalogo, ma contextual debole; se serve, come "per unita di valore aggiunto", che qui non ho verificato.
- Rifiuti urbani indifferenziati pro capite (kg/abitante): dal CSV comunale `https://www.catasto-rifiuti.isprambiente.it/get/getDettaglioComunale.csv.php?&aa=2024` (7.899 righe comunali, 2024, scaricato) aggregato per provincia (107). Esempi calcolati: alto Palermo 297,6; medio Biella 146,5; basso Treviso 46,5 kg/ab. Quasi doppione: e RU meno RD, gia coperti da "Rifiuti urbani prodotti" e "Raccolta differenziata dei rifiuti urbani". Lo terrei solo se si vuole il numero crudo "indifferenziato".
- Ozono: vedi punto 3.

## Scartati e perche

- Produzione di rifiuti urbani pro capite, raccolta differenziata (ISPRA): doppione di "Rifiuti urbani prodotti" e "Raccolta differenziata dei rifiuti urbani" (province 2024 gia scaricabili: `getRaccoltaProvinciale.csv.php?pg=provincia&aa=2024`, 107 righe). Non nuovi.
- Rifiuti urbani in discarica, compostaggio, servizio di raccolta: nomi gia in catalogo ("Conferimento dei rifiuti urbani in discarica", "Rifiuti urbani smaltiti in discarica per abitante", "frazione umida trattata in impianti di compostaggio").
- Riciclo/preparazione per il riutilizzo %: il Catasto non da un CSV di questo indicatore che abbia verificato (e nel rapporto in PDF a livello regionale). Non verificato, non proposto.
- Consumo di suolo ISPRA: escluso, e gia coperto da un altro lavoro.
- Popolazione esposta a rischio frane/alluvioni: doppione ("Popolazione esposta a rischio frane/alluvioni" nel catalogo).
- Siti contaminati ("Siti contaminati", "Gestione dei siti contaminati"), aree protette ("Aree protette", "Aree terrestri protette", "Siti di Importanza Comunitaria"), PM2.5, verde urbano ("Disponibilita di verde urbano", "Verde pubblico nelle citta"), rinnovabili sui consumi, incendi, depurazione, acque: doppioni in catalogo.
- ISPRA ambiente urbano: non verificato; per natura copre i comuni capoluogo, non le 107 province: non l'ho aperto.
- Operatori biologici per provincia (SINAB): non trovato un file provinciale; il rapporto 2025 ha solo regioni per operatori e superfici. Non verificato altrove, scartato.
- Atlaimpianti (GSE): trovata la pagina `https://www.gse.it/dati-e-scenari/atlaimpianti`, ma nessun file scaricabile verificato; uso il PDF del rapporto fotovoltaico.
- Protezione Civile, ARERA, MASE, ISPRA ambiente urbano, CORINE: non verificati, non esplorati per limiti di tempo. Non sono scartati nel merito.

## Elenco dei file scaricati (`lavoro/parti/fonti_ambiente/`)

`idrogeo_province_pir.json` (107 province, API IdroGEO), `idrogeo_province_elenco.json`, `idrogeo_rapporto_2024.pdf` e `.txt`, `ru_prov_2024.csv`, `ru_comuni_2024.csv`, `rs_prod_reg_2023.csv`, `rs_gest_reg_2023.csv`, `no2_isqa_2024.csv`, `o3_isqa_2024.csv`, `gse_fv_2024.pdf` e `.txt`, `terna_consumi_2024.pdf` e `.txt`, `sinab_bic_2025.pdf` e `.txt`, piu pagine html di appoggio.

---

# Ricerca indicatori nuovi: area SALUTE (fonti non Istat-SDMX)

Data della ricerca: 1 ottobre 2026. Ogni fonte e' stata aperta con curl il giorno stesso. I file scaricati stanno in `lavoro/parti/fonti_salute/`. Doppioni verificati con grep su `lavoro/parti/catalogo_nomi.txt` (parole: vaccin, screening, farmac, consult, medic, assist, ricover, psich, posti, ospiti).

Esito del grep sul catalogo: NESSUNA voce su vaccinazioni, screening oncologici, farmacie, consultori, salute mentale (utenti DSM). Voci vicine gia' presenti: "Medici di medicina generale con un numero di assistiti oltre soglia", "Medici", "Medici specialisti", "Infermieri e ostetriche", "Posti letto negli ospedali", "Anziani trattati in assistenza domiciliare integrata", "Presa in carico degli anziani per il servizio di assistenza domiciliare integrata", "Ospiti anziani non autosufficienti dei presidi residenziali ... per centomila anziani", "Posti letto nei presidi residenziali socio-assistenziali e socio-sanitari", "Dimissioni ospedaliere di pazienti affetti da disturbi psichici", "Emigrazione ospedaliera in altra regione", "Fumo/Alcol/Sedentarieta' (tassi standardizzati)", "Rinuncia a prestazioni sanitarie".

Nota trasversale sul territorio: quasi tutta la sanita' ufficiale non-Istat arriva a livello regionale (le Province autonome di Bolzano e Trento compaiono separate; per il sito si sommano in TAA). Il livello provinciale esiste solo per le anagrafiche (farmacie) e per i dati ASL.

---

## CANDIDATI

### 1. Copertura vaccinale antinfluenzale negli anziani (65 anni e piu')

1. Nome pubblico: "Copertura vaccinale antinfluenzale negli anziani" (65+). Istituzione: Ministero della Salute (Direzione generale della prevenzione sanitaria / Ufficio malattie trasmissibili). Esiste anche la serie sulla popolazione generale (stesso file).
2. Dato scaricabile: https://www.salute.gov.it/new/sites/default/files/2025-09/C_17_bancheDati_37_0_0_file%20%282%29.xls (xls, aggiornato alle stagioni fino a 2023-24) e https://www.salute.gov.it/new/sites/default/files/2025-09/2025_0035314_Confronti_CV_Antinfluenzali_1999_2025.pdf (PDF di 2 pagine con la serie 1999-00 / 2024-25, gia' la stagione piu' recente). Pagina di metodo: https://www.salute.gov.it/new/it/banche-dati/vaccinazione-antinfluenzale-coperture-vaccinali-medie/ e https://www.salute.gov.it/new/it/tema/influenza/dati-coperture-vaccinali-influenza/ . Licenza: nelle note legali (https://www.salute.gov.it/new/it/altro/note-legali-2/) si legge: "I contenuti pubblicati sul presente sito www.salute.gov.it sono messi a disposizione con licenza CC-BY 4.0 - Attribuzione." (ok per il riuso con citazione della fonte). Sulla pagina del dato non c'e' una licenza propria: vale quella generale del sito.
3. Livello: regioni, 21 righe (Bolzano e Trento separate, quindi 20 regioni con TAA sommata o media pesata da fare; la media TAA non si puo' calcolare senza i denominatori degli anziani). Riga Italia inclusa.
4. Anni: stagioni dal 1999-00 al 2024-25 (PDF) o 2023-24 (xls), annuale (stagione). Ultimo 2024-25, ben oltre 2023.
5. Unita': percentuale (dosi somministrate su popolazione target di 65+), RELATIVO.
6. Verso: higher_better.
7. Doppione: NUOVO (nessuna voce "vaccin*" nel catalogo; "Anziani trattati in ADI" e' tutt'altro).
8. Esempio dal file (65+, stagione 2024-25, PDF): alto Umbria 64,1%; basso Sardegna 37,6%; medio Italia 52,5%. (Stesso file xls, 2023-24: Umbria 65,78; Sardegna 35,75; Italia 53,28.)
9. Difficolta': bassa/media. Il xls e' ben strutturato (regioni in riga, stagioni in colonna, due blocchi: popolazione generale righe 2-23, anziani righe 27-48). Serve scegliere xls (fino a 2023-24) oppure estrarre il PDF per l'ultima stagione (testo selezionabile, parsabile con pypdf). Etichette regione irregolari ("P. A. Trento", "P.A. Bolzano"). Gli URL del xls hanno suffissi "(2)" e cambiano a ogni ripubblicazione: va fissato lo URL e documentata la data di scarico. Attenzione: la "stagione" 2023-24 va associata all'anno solare con una convenzione dichiarata.

### 2. Copertura vaccinale a 24 mesi per morbillo (1a dose) e per ciclo base esavalente

1. Nome pubblico: "Copertura vaccinale a 24 mesi" (morbillo, 1a dose; poliomielite/difterite/tetano/pertosse/epatite B/Hib ciclo di base; pneumococco; varicella; rotavirus; meningococco). Istituzione: Ministero della Salute (Direzione generale delle emergenze sanitarie, Ufficio 2 Prevenzione e profilassi delle malattie trasmissibili).
2. Dato scaricabile: PDF https://www.salute.gov.it/new/sites/default/files/2025-12/Allegato%202_Tabelle%20CV-1.pdf (coperture a 24 mesi, anno 2024, coorte 2022); sono anche disponibili CV-2...CV-7 (36 mesi, 48 mesi, 5-6, 8, 16, 18 anni) e il commento tecnico https://www.salute.gov.it/new/sites/default/files/2025-12/Allegato%201_Commento%20tecnico.pdf . Pagina di metodo: https://www.salute.gov.it/new/it/banche-dati/vaccinazioni-delleta-pediatrica-e-delladolescenza-coperture-vaccinali/ ("Periodo di riferimento: dal 2000 al 2024. Frequenza di aggiornamento: annuale"; dati "autodichiarati dalle Regioni e Province Autonome"). Licenza: la stessa del sito, "licenza CC-BY 4.0 - Attribuzione" (note legali); sulla pagina specifica non c'e' una licenza propria.
3. Livello: regioni, 21 righe (PA Bolzano e Trento separate, piu' Italia).
4. Anni: serie annuale dal 2000 (con tabelle diverse per eta') al 2024. Per il 24 mesi con tutti gli antigeni: 2013-2024. Ultimo 2024.
5. Unita': per 100 residenti della coorte (percentuale), RELATIVO.
6. Verso: higher_better.
7. Doppione: NUOVO.
8. Esempio dal file CV-1 (anno 2024, coorte 2022, a 24 mesi, morbillo = colonna MOR): alto Lombardia 98,10; basso Sicilia 87,98; medio Italia 94,77. (Per esavalente/polio: Lombardia 98,30, Sicilia 85,13, Italia 94,45.)
9. Difficolta': MEDIA/ALTA. Solo PDF, un file per eta' e per anno, impaginazione che cambia negli anni (le tabelle 2013-2019 hanno colonne diverse; compaiono "n.d."). Estrazione testo OK con pypdf per l'anno 2024; va costruito un parser per ogni formato di anno oppure ci si limita agli ultimi 5-6 anni (2019-2024). Rischio di rottura dei link a ogni rilascio. Si consiglia un solo indicatore (morbillo 1a dose a 24 mesi, sensibile alle soglie OMS del 95%) piu' eventualmente HPV. Nota di verso: le coperture alte non vanno interpretate come "giudizio" sul territorio ma sono un indicatore di servizio.

### 3. Farmacie ogni 10.000 abitanti (provincia)

1. Nome pubblico: "Farmacie ogni 10.000 abitanti" (farmacie ordinarie aperte al pubblico). Istituzione: Ministero della Salute (Direzione generale dei dispositivi medici e del servizio farmaceutico, Ufficio 9) per il numeratore; Istat per i residenti al denominatore (demo.istat.it, non esploradati).
2. Dato scaricabile: https://www.dati.salute.gov.it/sites/default/files/opendata/FRM_FARMA_5_20261001.csv (11 MB, CSV ";" , aggiornamento giornaliero; il nome file porta la data). Pagina di metodo e dizionario: https://www.dati.salute.gov.it/it/dataset/farmacie/ . Denominatore: https://demo.istat.it/data/posas/POSAS_2025_it_Province.zip (residenti per eta' al 1 gennaio 2025, 107 province). Licenza: sulla pagina del dataset "Licenza: Italian Open Data Licence v2.0" (link https://www.dati.gov.it/iodl/2.0/).
3. Livello: comune (cod_comune), provincia (cod_provincia, 111 codici nel file: vedi difficolta') e regione. Sulle 107 province: 103 corrispondono ai codici Istat 2025, 4 sono le province sarde storiche (104 Olbia-Tempio, 105 Ogliastra, 106 Medio Campidano, 107 Carbonia-Iglesias) che vanno riaccorpate dal comune.
4. Anni: il file e' un'istantanea con validita' per riga (data_inizio_validita / data_fine_validita, es. 01/01/2005-30/06/2023), quindi si ricostruisce la serie annuale dal 2012 (data di primo caricamento 11/05/2012) a oggi. Ultimo aggiornamento 01/10/2026. Frequenza giornaliera; per il sito basta una fotografia a fine anno. La storicita' dipende dalla correttezza delle date di validita' (non verificata anno per anno: da fare solo l'ultimo anno, o validare).
5. Unita': numero di farmacie per 10.000 residenti. Il file contiene solo anagrafica (conteggio), quindi il RELATIVO si calcola con denominatore Istat: va dichiarato. 19.856 farmacie "Ordinaria" attive + 110 con tipologia "-" (codice 1) ecc.; totale attive 20.771 includendo succursali, dispensari e stagionali; per l'indicatore si consiglia: tipologia codice 1 (ordinarie), esclusi dispensari e stagionali.
6. Verso: contextual (piu' farmacie per abitante puo' voler dire accessibilita' ma anche territorio rurale con pochi abitanti per sede; non dare giudizio).
7. Doppione: NUOVO. (Nel catalogo non c'e' nulla su farmacie.)
8. Esempio calcolato dal file (farmacie ordinarie attive al 1/10/2026, residenti al 1/1/2025): alto Isernia 7,11 per 10.000 (56 farmacie su 78.755 residenti); basso Bolzano/Bozen 2,52 (136 su 539.679); medio Arezzo 3,57 (119 su 333.240) o Lucca 3,54. Dato da non usare per la Sardegna senza rimappare le province storiche (Sud Sardegna calcolata a 1,03 perche' le farmacie di Carbonia-Iglesias e Medio Campidano sono sotto i codici 106/107).
9. Difficolta': MEDIA. Punti critici: (a) mappare le 4 province sarde storiche e Monza/Brianza, Fermo, Barletta-Andria-Trani sui codici del catalogo; (b) separare tipologie (ordinaria, succursale, dispensario); (c) ricostruire gli anni passati dalle date di validita', con righe duplicate per cambio di titolare (stesso cod_farmacia con piu' partite IVA); (d) rischio rifacimento Sardegna 2026 (nuove province): il sito ha gia' un tema "confini e Sardegna". (e) coordinate geografiche a volte "-". Il file e' molto grande (11 MB): scaricarlo e aggregarlo, non versionarlo.

### 4. Screening oncologici: cervicale, mammografico, colorettale (PASSI, Istituto Superiore di Sanita')

1. Nome pubblico: "Donne 25-64 anni con screening cervicale in regola" / "Donne 50-69 anni con screening mammografico in regola" / "Persone 50-69 anni con screening colorettale in regola" (copertura totale = organizzata + spontanea). Istituzione: Istituto Superiore di Sanita', sorveglianza PASSI (Progressi delle Aziende Sanitarie per la Salute in Italia), EpiCentro.
2. Dato: non esiste un file scaricabile. Le pagine https://www.epicentro.it/passi/ARG014/I.B.aspx (cervicale), ARG015 (mammografico), ARG016 (colorettale; i codici ARG sono quelli letti dalle pagine https://www.epicentro.iss.it/passi/dati/ScreeningCervicale|ScreeningMammografico|ScreeningColorettale) caricano i valori con una chiamata POST al servizio `https://www.epicentro.it/passi/JServices/GroupData.ashx` con parametri Periodo, ARG, Livello (100 = Italia; 01..20 regioni; 421 Bolzano; 422 Trento), CodiceGruppo=B. Ho verificato che risponde in XML (i file sono in `fonti_salute/passi/`). E' un endpoint interno del sito, non un'API documentata. Pagina di metodo: https://www.epicentro.iss.it/passi/infoPassi/infoGen e https://www.epicentro.iss.it/passi/infoPassi/protocollo-operativo-passi . Licenza: NON TROVATA. Ho cercato nelle pagine PASSI e nelle note legali di EpiCentro senza leggere una frase di licenza (cartelle /informazioni/copyright 404 o senza testo): **licenza non verificata, ambigua**. Va chiesto all'ISS/PASSI (passi@iss.it) prima di scaricare in modo sistematico.
3. Livello: regioni; 2023-2024: 20 unita' su 21 (manca la Lombardia, non partecipa a PASSI in quel biennio), PA Bolzano e Trento separate (nessun dato a livello provinciale pubblico). Con TAA la Lombardia manca comunque: l'indicatore avrebbe 19 regioni su 20.
4. Anni: periodi di 4 anni fino al 2016-2019, poi biennali: 2020-2021, 2021-2022, 2022-2023, 2023-2024 (e 2011-2014 ... 2015-2018 come finestre mobili di 4 anni). Quindi NON e' una serie annuale omogenea: la serie ha cambio di ampiezza della finestra. Ultimo periodo 2023-2024.
5. Unita': percentuale (di donne/persone nella fascia, intervistate, che hanno fatto il test nei tempi raccomandati), RELATIVO. E' una indagine campionaria (n regionale 362-2.763 per cervicale), con IC 95%.
6. Verso: higher_better.
7. Doppione: NUOVO (nulla su screening nel catalogo).
8. Esempio (cervicale totale, 2023-2024, letto dal servizio PASSI): alto Friuli Venezia Giulia 89,6% (n=2.763); basso Calabria 58,7% (n=608); medio Italia 77,7% (n=27.852). Mammografico: FVG 89,9%, Calabria 46,2%, Italia 74,9%. Colorettale: Veneto 73,9%, Calabria 15,5%, Italia 47,4%. Nel 2012-2015: cervicale Italia 79,2% (ER 90,3; Calabria 58,3).
9. Difficolta': ALTA. Nessun download, endpoint POST non documentato, licenza da chiarire, Lombardia mancante, finestre non annuali, campione con intervalli di confidenza da mostrare. Alternativa piu' pulita non verificata: i dati dell'Osservatorio Nazionale Screening (ONS) e i dati LEA/NSG del Ministero, che non ho aperto. Raccomandazione: tenere in lista d'attesa fino al chiarimento della licenza.

---

## SCARTATI (con il motivo)

- **Consultori familiari (Ministero della Salute, open data)**: https://www.dati.salute.gov.it/it/dataset/consultori-familiari-anno-2022/ (CSV, anno 2022 soltanto, IODL 2.0, elenco per struttura con comune/provincia, scaricato in `consultori2022.csv`). Scartato come indicatore pronto: il dato e' un ELENCO (assoluto) e l'ultimo anno e' 2022 (richiesto >= 2023). L'Annuario SSN 2023 (xlsx, sotto) ha il conteggio regionale 2014-2023 (es. Emilia-Romagna 332, Sardegna 71, Italia 2.140 nel 2023) ma e' assoluto: serve denominatore (donne 15-49 o residenti) e le definizioni cambiano (PA Bolzano 33 -> 68 tra 2022 e 2023, una discontinuita'). Riconsiderabile come "consultori per 100.000 donne 15-49 anni" se il costo del denominatore e' accettato.
- **Posti residenziali per anziani per 1.000 anziani (Annuario statistico SSN 2023)**: https://www.salute.gov.it/new/sites/default/files/imported/C_17_pubblicazioni_3523_0_alleg.xlsx (foglio `T_Ass_Res_Semires_Anziani`, 2014-2023, regioni, ottima struttura, unita' per 1.000 anziani). Scartato come QUASI DOPPIONE di "Posti letto nei presidi residenziali socio-assistenziali e socio-sanitari" e "Ospiti anziani non autosufficienti ... per centomila anziani" (Istat). Se si vuole la fonte ministeriale, e' una variante da decidere. Ci sono anche `T_Ass_Res_Semires_Disabili` (posti per 10.000 residenti) e `T_Ass_Res_Semires_Psic` (posti psichiatrici per 10.000): stessa logica, vicine a "Ospiti adulti con disabilita' o patologia psichiatrica ...". Licenza dell'Annuario: CC-BY 4.0 del sito, non una licenza specifica del file.
- **Scelte per medico di medicina generale / medici generici per classe di scelte (Annuario SSN 2023, foglio `ASS_DIS_MED_02`)**: numero medio di scelte per medico, per regione, 2023 (Italia 1.335; Molise 1.052, Lombardia 1.547). Scartato come DOPPIONE sostanziale di "Medici di medicina generale con un numero di assistiti oltre soglia" gia' in catalogo. Il file ha un foglio per anno, non una serie.
- **ADI: ore e accessi per caso trattato (Annuario SSN 2023, `ASS_DIS_DOM_01 I/II/III`)**: scartato, qualita' del dato: pieno di valori sentinella (-0,0001, "_"), molte regioni senza personale per profilo; inoltre il catalogo ha gia' tre voci ADI. 
- **Utenti trattati nei Dipartimenti di salute mentale (Ministero, open data 2020-2024)**: https://www.dati.salute.gov.it/it/dataset/prevalenza-degli-utenti-trattati-nei-dsm-sesso-e-gruppo-diagnostico-2024/ (CSV `dsm_prevalenza_2024.csv`, IODL 2.0, regioni/ASL/DSM). Scartato: copertura regionale incompleta (l'Abruzzo manca del tutto; il Molise ha 303 casi, tasso 105 per 100.000 contro 10.054 dell'Emilia-Romagna: differenza di trasmissione, non di salute) e colonna "Numero Accessi" ambigua. Riconsiderare solo con le regioni a copertura completa.
- **Personale dei SERD, dei DSM, personale dipendente delle ASL (Ministero, open data)**: CSV con righe per struttura (SERD 2023 scaricato), tutti assoluti; per renderli relativi servono denominatori. "Medici", "Infermieri" e simili sono gia' in catalogo (doppione per il personale ASL).
- **Posti letto ospedalieri per regione e disciplina (Ministero 2010-2023)**: DOPPIONE ("Posti letto negli ospedali", "Posti letto per specialita' ad elevata assistenza").
- **Dimissioni ospedaliere (Ministero, open data)**: assoluti e vicini a voci gia' presenti (dimissioni per disturbi psichici, emigrazione ospedaliera).
- **AGENAS Programma Nazionale Esiti (PNE) e Piattaforma Nazionale Liste di Attesa (PNLA)**: https://pne.agenas.it/ e https://www.portaletrasparenzaservizisanitari.it/pnla/ sono raggiungibili ma sono cruscotti interattivi (applicazione web), senza un file CSV scaricabile individuato nelle pagine; la PNLA pubblica dati dal 2025 (gennaio-settembre 2025) con tempi di attesa per classe di priorita', a livello di regione/azienda. Il catalogo dei dati AGENAS (https://www.agenas.gov.it/altri-contenuti/accessibilita-e-catalogo-di-dati-metadati-e-banche-dati) elenca fonti ma non ho letto una licenza. **NON VERIFICATO** a livello di file/licenza: il dato di esito (es. mortalita' a 30 giorni dopo IMA) e' certamente interessante ma richiede estrazione da dashboard, quindi non e' un candidato pronto.
- **HPV, copertura (Ministero)**: https://www.salute.gov.it/new/it/banche-dati/vaccinazione-contro-il-papilloma-virus-hpv-coperture-vaccinali/ solo PDF per coorti di nascita (2015-2024), regioni. Possibile estensione del candidato 2 (stessa licenza, stessa difficolta' PDF); non l'ho estratta.
- **Medici di base per 1.000 abitanti e altri dati di personale a livello regionale**: i totali MMG sono nell'Annuario SSN 2023 (`ASS_DIS_MED_01`), ma mancano le serie e il denominatore e' da costruire; vicino a "Medici" gia' in catalogo.
- **Istat Health for All (HFA)**: non verificato. Il database HFA e' su https://www.istat.it/ ma i dati correnti sono serviti da esploradati; escluso dalle istruzioni.
- **Fascicolo sanitario, ticket, esenzioni, liste d'attesa regionali**: non aperti per limiti di tempo; il Fascicolo sanitario elettronico e' gia' in catalogo.

---

## Riepilogo e raccomandazione

| # | Indicatore | Fonte | Livello | Ultimo anno | Difficolta' | Licenza |
|---|---|---|---|---|---|---|
| 1 | Copertura antinfluenzale 65+ | Ministero della Salute | 21 regioni | 2024-25 | bassa/media | CC-BY 4.0 (sito) |
| 2 | Copertura vaccinale a 24 mesi (morbillo) | Ministero della Salute | 21 regioni | 2024 | media/alta (PDF) | CC-BY 4.0 (sito) |
| 3 | Farmacie ogni 10.000 abitanti | Ministero della Salute + Istat | 107 province | 2026 (serie da ricostruire) | media | IODL 2.0 |
| 4 | Screening (3 indicatori) | ISS / PASSI | 20 regioni su 21 | 2023-2024 | alta | NON verificata |

Ordine consigliato: 1 (piu' pulito), poi 3 (unico provinciale, ma Sardegna da gestire), poi 2. Il 4 aspetta la risposta sulla licenza. Per tutti: attribuzione esplicita "Ministero della Salute" o "Istituto Superiore di Sanita'", nome dell'istituzione in chiaro, da registrare in `app/sources.py`.

---

# Ricerca fonti: istruzione e giustizia/servizi (1 ottobre 2026)

Sola ricerca, nessuna modifica al codice. File scaricati in `lavoro/parti/fonti_scuola/`.
Tutte le cifre degli esempi sono calcolate da me sui file scaricati (non dalla memoria).
Controllo doppioni fatto su `lavoro/parti/catalogo_nomi.txt` con grep per parola chiave.

Fonti aperte con successo: portale Unico dei dati MIM (`dati.istruzione.it/opendata`), portale open data MUR-USTAT (`dati-ustat.mur.gov.it`, API CKAN), pagine statistiche del Ministero della Giustizia.
Fonti NON verificate: ARERA, AGCOM, MIMIT, MASE (vedi scartati).

Nota comune MIM. Licenza: la scheda di ogni dataset, sezione "Tracciato record", riporta "Licenza: IODL 2.0" (letto sulle pagine leaf di `DS0090ALUTEMPOSCUOLASTA`, `DS0280EDICONSICUREZZASTA`, `DS0210EDIAMBFUNZSTA`). Frase letta: "Licenza: IODL 2.0" (Italian Open Data License 2.0, richiede attribuzione). Nei dataset "STA" (scuole statali) la copertura dichiarata è "Dati nazionali con esclusione delle province autonome di Trento e Bolzano"; di fatto il file alunni/docenti non contiene neppure la Valle d'Aosta (18 regioni, 104 province su 107). Le scuole paritarie sono in file "PAR" separati (stessa struttura, non sommati nei miei esempi). Attribuzione consigliata: "Ministero dell'Istruzione e del Merito, Portale Unico dei dati della scuola".

URL di base dei file: `https://dati.istruzione.it/opendata/opendata/catalogo/elements1/<NOMEFILE>.csv` (verificato 200, CSV senza login). Pagina di metodo (tracciato record, copertura, licenza): `https://dati.istruzione.it/opendata/opendata/catalogo/elements1/leaf?area=<Area>&datasetId=<DS...>`.

---

## CANDIDATI (5)

### 1. Alunni della primaria a tempo pieno

1. Nome: "Alunni della scuola primaria a tempo pieno" (%). Istituzione: Ministero dell'Istruzione e del Merito.
2. Dato: `.../elements1/ALUTEMPOSCUOLASTA20242520250831.csv` (una riga per scuola, anno di corso, tempo scuola). Metodo: `.../elements1/leaf?area=Studenti&datasetId=DS0090ALUTEMPOSCUOLASTA`. Licenza: "IODL 2.0".
3. Livello: scuola (`CODICESCUOLA`), da aggregare a provincia con l'anagrafe `SCUANAGRAFESTAT20242520250831.csv` (colonne REGIONE, PROVINCIA; join con 0 scuole mancanti). Copre 104 province su 107 (mancano AO, BZ, TN) e 18 regioni su 20 (mancano VdA e TAA). I nomi provincia sono maiuscoli (es. "SUD SARDEGNA", "MONZA E DELLA BRIANZA").
4. Anni: a.s. 2015/16 - 2024/25 (10 file, uno per anno), annuale, aggiornato al 31 agosto. Ultimo 2024/25 (>= 2023 ok).
5. Unità: % di alunni (somma ALUNNIMASCHI+ALUNNIFEMMINE con TEMPOSCUOLA = "TEMPO PIENO" sul totale della primaria statale). Relativo, nessun assoluto.
6. Verso: higher_better (con cautela, è offerta di servizio; la domanda varia). Se si preferisce prudenza: contextual.
7. Doppione: grep "tempo pieno|tempo scuola" nel catalogo = nessuna riga. NUOVO.
8. Esempio (a.s. 2024/25, primaria statale): alto Milano 97,1% (116.980 alunni); basso Isernia 2,8% (2.787); mediana Sondrio 35,9%; Italia (aggregato file) 44,0%. Altri bassi: Palermo 6,8%, Siracusa 12,5%.
9. Difficoltà: media. Join scuola->provincia, esclusione AO/BZ/TN da dichiarare; solo statali (paritarie escluse, vanno in nota). Occhio: il campo TEMPOSCUOLA vale "TEMPO NORMALE/TEMPO PIENO" per la primaria e "INDIRIZZO ORDINARIO/MUSICALE" per la secondaria I grado, filtrare ORDINESCUOLA = "SCUOLA PRIMARIA".

### 2. Docenti supplenti sul totale dei docenti

1. Nome: "Docenti con contratto da supplente" (% sul totale docenti). Istituzione: Ministero dell'Istruzione e del Merito.
2. Dato: `.../elements1/DOCSUPXXV20242520250831.csv` (supplenti) e `.../elements1/DOCTIT20242520250831.csv` (titolari), già per PROVINCIA. Metodo: `.../leaf?area=Personale Scuola&datasetId=DS9999DOCSUPXXV` e `DS0600DOCTIT`. Licenza: "IODL 2.0" (stessa famiglia di dataset del portale; letta esplicitamente sulle schede Studenti ed Edilizia, la scheda Personale non l'ho riaperta una a una: non verificato per questi due).
3. Livello: provincia (104 su 107, mancano AO, BZ, TN; 104 nomi in entrambi i file). Regioni: 18 su 20.
4. Anni: DOCTIT/DOCSUP presenti fino al 2024/25; il primo anno non l'ho verificato (non ho aperto l'elenco file del Personale). Annuale.
5. Unità: % = supplenti / (supplenti + titolari). Relativo. Attenzione: è un conteggio di contratti/persone supplenti, non di posti equivalenti (nel file con tipo "ANNUALE" e "FINO AL TERMINE" delle attività didattiche; 1.156 righe su 9.989 con contratto finalizzato al ruolo).
6. Verso: lower_better (precarietà e discontinuità didattica). Variante più netta: solo posti di SOSTEGNO.
7. Doppione: grep "docent|insegnant|supplent|precari" nel catalogo = nessuna riga. NUOVO.
8. Esempio 2024/25 (statale): alto Vercelli 35,3% (1.121 supplenti su 3.179); basso Caserta 8,2% (1.376 su 16.737); mediana Parma 26,0%; Italia 24,3%. Sul solo sostegno: Lodi 77,3%, Caserta 18,1%, mediana Livorno 58,3%.
9. Difficoltà: bassa. File già per provincia, nessun join. Rischio interpretativo: il nord ha più supplenti per carenza di candidati/abilitati e meno per scelta; indicare in prosa. Verso editoriale da concordare.

### 3. Alunni per classe

1. Nome: "Alunni per classe" (numero medio). Istituzione: Ministero dell'Istruzione e del Merito.
2. Dato: `.../elements1/ALUCORSOINDCLASTA20242520250831.csv` (colonne CLASSI, ALUNNIMASCHI, ALUNNIFEMMINE per scuola e anno di corso). Metodo: `.../leaf?area=Studenti&datasetId=DS0030ALUCORSOINDCLASTA`. Licenza: "IODL 2.0" (stessa nota del blocco).
3. Livello: scuola, aggregato a provincia con l'anagrafe statale (104/107, 18/20 regioni).
4. Anni: 2015/16 - 2024/25 per gli altri file del gruppo Studenti (primo anno di questo file non aperto: da verificare); annuale; ultimo 2024/25.
5. Unità: alunni per classe (somma alunni / somma classi). Relativo.
6. Verso: contextual (troppe classi affollate è negativo, ma classi piccole segnalano denatalità e piccole sedi di montagna/isole).
7. Doppione: grep "per classe|classi" nel catalogo: solo le voci INVALSI "studenti classi II/III/V" (livelli di competenza), nessuna sul numero di alunni per classe. NUOVO.
8. Esempio 2024/25 (tutti gli ordini statali): alto Ravenna 21,6 (40.577 alunni in 1.875 classi); basso Sud Sardegna 14,6 (27.384/1.881); mediana Perugia 18,8; Italia 18,9. Solo secondaria II grado: Forlì-Cesena 22,6, Nuoro 15,1, mediana Lucca 19,6.
9. Difficoltà: media (join scuola->provincia, scegliere se per ordine di scuola; consiglio totale + serie per ordine).

### 4. Edifici scolastici con palestra

1. Nome: "Edifici scolastici dotati di palestra" (%). Istituzione: Ministero dell'Istruzione e del Merito, Anagrafe nazionale dell'edilizia scolastica.
2. Dato: `.../elements1/EDIAMBFUNZSTA202120242520250806.csv` (colonne PALESTRA, MENSA, AUDITORIUM, PISCINA, per CODICEEDIFICIO) e `.../elements1/EDIANAGRAFESTA202120242520250806.csv` (CODICEEDIFICIO -> SIGLAPROVINCIA). Metodo: `.../leaf?area=Edilizia Scolastica&datasetId=DS0210EDIAMBFUNZSTA`. Licenza: "IODL 2.0"; periodicità letta: "Aggiornamento non periodico". I dati sono "forniti dagli Enti locali proprietari o gestori degli edifici ai sensi della legge 11 gennaio 1996, n. 23".
3. Livello: edificio, con SIGLAPROVINCIA nel file anagrafica: 105 province (include Aosta, esclude BZ e TN). Regioni 19 su 20 (manca TAA).
4. Anni: file cumulativi 2020/21 - 2024/25 (cinque istantanee annuali di anagrafe, pubblicate 2025-08-06 per l'ultima). Ultimo 2024/25.
5. Unità: % di edifici (CODICEEDIFICIO unici, 39.351 nel 2024/25; PALESTRA = "SI" su totale edifici). Relativo.
6. Verso: higher_better (dotazione), con cautela: una scuola dell'infanzia non ha bisogno di palestra, quindi l'indicatore va letto come dotazione degli edifici e non come "diritto".
7. Doppione: nel catalogo c'è "Sicurezza degli edifici scolastici" e "Scuole accessibili" (Istat/BDTPS, fonte MIUR Anagrafe edilizia, regione, serie ferma al 2012 secondo `data/definitions/istat_territoriali.csv`). La palestra/mensa non sono nel catalogo. NUOVO (e il dato del catalogo ha un buco di 10 anni).
8. Esempio 2024/25 (province con almeno 20 edifici): alto Monza e Brianza 59,4% (406 edifici); basso Catanzaro 17,4% (391); mediana Roma 38,8% (1.894); Italia 38,2%. Anche Cosenza 20,0%, Vibo Valentia 21,3%.
9. Difficoltà: alta rispetto ai primi tre. Join a due file, qualità della compilazione disomogenea (autodichiarazione degli enti; 357 edifici con "NON DEFINITO"), serie breve e con aggiornamento non periodico, copertura edificio non scuola (un edificio ospita più scuole: si conta una volta). Da rivedere con attenzione prima di metterlo nello scoring.

### 5. Iscritti universitari che studiano fuori dalla regione di residenza

1. Nome: "Studenti universitari che studiano fuori regione" (% degli iscritti residenti nella regione). Istituzione: Ministero dell'Università e della Ricerca, Ufficio di statistica (USTAT).
2. Dato: CSV `https://dati-ustat.mur.gov.it/dataset/3dd9ca7f-9cc9-4a1a-915c-e569b181dbd5/resource/42446e78-9baa-4c82-9c56-251ce43654f4/download/14b_iscrittixresidenzasedecorsoclasse.csv` (AnnoA, ClasseNUMERO, SedeR, ResidenzaR, Isc). Variante provinciale: `.../resource/b270ef1a-c219-48b1-8399-b1458e225d39/download/14a_iscrittixresidenzasedecorsogruppo.csv` (ResidenzaP, SedeP codice Istat provincia sede). Metodo: scheda `https://dati-ustat.mur.gov.it/dataset/iscritti` e foglio "Descrizione tracciato record" `.../resource/0c3d5cc9-daab-4a04-89c4-131b0141f884/download/00_iscritti_info.xlsx` (14a/14b: "le occorrenze minori di 5 sono state escluse; sono esclusi gli iscritti alle Università telematiche", elaborazione su dati ANS ottobre 2025). Licenza: metadati API CKAN: "license_title": "Italian Open Data License v2.0", "license_id": "IODL-2.0".
3. Livello: regione (20 regioni con Bolzano e Trento separate: da sommare come TAA). Il file 14a dà anche la provincia di residenza, ma i nomi sono diversi da quelli del file immatricolati (109 vs 112 nomi, ancora presenti Medio Campidano, Sulcis Iglesiente, Ogliastra; SedeP a volte "NULL"): per la scala provinciale serve una tavola di raccordo, non fatta qui.
4. Anni: a.a. 2010/11 - 2024/25, annuale. Ultimo 2024/25 (>= 2023 ok).
5. Unità: % = iscritti con SedeR diversa da ResidenzaR / iscritti totali residenti (esclusi "REGIONE ESTERA" e "REGIONE NON FORNITA"). Relativo.
6. Verso: contextual (alta = pochi corsi/poca offerta locale o scelta di mobilità; bassa = attrattività o poli grandi come Lombardia e Lazio). Non è un giudizio.
7. Doppione: nel catalogo ci sono "Indice di attrattività delle università" (lato sede), "Mobilità dei laureati italiani (25-39 anni)" (lato laureati, migrazione post-laurea) e "Passaggio all'università". Questo è il lato residenza degli iscritti, diverso e misurabile sul solo dato MUR. Nessuna voce uguale. NUOVO ma tematicamente vicino a "attrattività": dichiararlo come complementare nella prosa.
8. Esempio 2024/25 (TAA aggregato, 20 regioni): alto Basilicata 73,4% (16.213 iscritti), Valle d'Aosta 66,8%; basso Lombardia 13,8% (231.776), Lazio 8,7% (184.073); mediana Friuli-Venezia Giulia 27,3%; Italia 20,8%. Nel 2018/19: Basilicata 70,3%, Lazio 9,2%.
9. Difficoltà: bassa a livello regionale (un solo file, 6 MB), media a livello provinciale (raccordo nomi). Nota: esclude le telematiche, quindi sottostima gli iscritti residenti.

---

## RISERVE (non nei 5, ma verificati)

- Alunni con cittadinanza non italiana (%). Dato: `.../elements1/ALUITASTRACITSTA20242520250831.csv`, scheda `leaf?area=Studenti&datasetId=DS0050ALUITASTRACITSTA`, IODL 2.0, stessa copertura (104 province). Verso contextual. NUOVO nel catalogo (grep "cittadinanza|stranier": solo occupazione degli stranieri). Esempio 2024/25: alto Prato 29,8% (29.449 alunni), basso Oristano 1,9% (13.767), mediana Udine 12,8%, Italia 12,0%. Facile e solido, è il sesto candidato: lo metto fuori solo per il limite di 5 e perché è più demografia che istruzione.
- Edifici scolastici con mensa (%): stesso file di palestra. Esempio: alto Aosta 71,9% (139), basso Ragusa 3,7% (215), Italia 36,5%. Stesse cautele di 4.
- Detenuti presenti su capienza regolamentare (sovraffollamento, %). Ministero della Giustizia, Dipartimento dell'amministrazione penitenziaria. Pagina: `https://www.giustizia.it/giustizia/it/mg_1_14_1.page?contentId=SST1518875` ("Detenuti italiani e stranieri presenti e capienze per istituto - aggiornamento 31 agosto 2026"), solo tabella HTML (nessun CSV; l'ho estratta in `giustizia_detenuti_capienza_2026-08-31.csv`, 189 istituti, regione e città dell'istituto, non il codice provincia). LICENZA: nessuna licenza aperta. Le Note legali (`https://www.giustizia.it/giustizia/page/it/note_legali`) dicono che l'utilizzazione e la riproduzione sono autorizzate "esclusivamente nei limiti in cui le stesse avvengano nel rispetto dell'interesse pubblico all'informazione, per finalità non commerciali, garantendo l'integrità" dei contenuti. Il sito divarioitalia ha pubblicità? Se sì, rischio da chiarire con Nello. Regioni: 20 (TAA come "TRENTINO ALTO ADIGE"). Esempio 31/08/2026 (somma istituti per regione, capienza regolamentare): alto Puglia 162,8% (4.788 presenti su 2.941), Lombardia 152,5%; basso Valle d'Aosta 85,1% (154 su 181), Sardegna 94,9%; mediana Campania 130,5%; Italia 128,2% (65.661 presenti su 51.220). Doppione: grep "detenut|carcer|sovraffoll" = nessuna riga. NUOVO ma bloccato dalla licenza e dalla serie storica (una pagina per mese, nessun archivio strutturato aperto). Verso: lower_better.

---

## SCARTATI e perché

- Dispersione scolastica / abbandoni MIM: nel catalogo MIM aperto (aree Scuole, Studenti, Personale, Edilizia, Sistema Nazionale di Valutazione, Adozioni) non ho trovato dataset su abbandoni o dispersione. Le voci "Tasso di abbandono ... scuole secondarie superiori" e "Uscita precoce" sono già nel catalogo (Istat). Doppione.
- Competenze INVALSI, scuole accessibili, alunni con disabilità, scuole per provincia: già nel catalogo (Istat/BES/MIUR). Doppioni.
- Anagrafe edilizia: certificato di agibilità (`CERTIFICATOSEGNALAZIONEAGIBILITA`) e certificato di prevenzione incendi: SI solo nel 37,2% (agibilità) e 34,1% (CPI) degli edifici a livello nazionale, con Aosta 87,8% e Trieste 5,2%, Cagliari 9,6%. Riflette soprattutto chi ha compilato e come lo prevede la legge (autodichiarazione degli enti locali), non la sicurezza reale: rischio di far dire al sito che un edificio non è sicuro. SCARTATO.
- MUR immatricolati per residenza (`05_immatricolatixresidenza.csv`, comune, sesso, fino al 2025/26): è un conteggio assoluto. Diventerebbe relativo (per 1.000 diciannovenni) solo con i denominatori Istat per età e provincia, che non ho aperto e che per la regola della task escluderebbero la via SDMX. Possibile solo con quei denominatori. Non verificato fuori da questo.
- MUR Diritto allo studio regionale (alloggi, mense, borse): dataset 2025 aperto (`2025-diritto-allo-studio-universitario-dsu-regionale`), ma riguarda posti alloggio e pasti per ente, non una misura relativa per territorio. Servirebbe un denominatore (studenti). SCARTATO per ora.
- Ministero della Giustizia, durata dei procedimenti per distretto: i "Monitoraggio civile e penale - Distretto di X - IV trimestre 2025" sono schede per distretto (26) in PDF/pagina. Il territorio è il distretto di Corte d'Appello, non coincide con province o regioni (es. più distretti per regione), e "Durata media effettiva in giorni dei procedimenti definiti presso i tribunali ordinari" è già nel catalogo. Doppione e territorio non mappabile. `webstat.giustizia.it` non raggiungibile da qui (connessione rifiutata/000). SCARTATO.
- ARERA (qualità servizi): ho aperto `https://www.arera.it/dati-e-statistiche`, è una pagina con sole informazioni sui cookie e un accesso a un portale riservato (raccolte dati via SSO, `rd.arera.it`). Non ho trovato un dataset scaricabile per provincia. NON VERIFICATO. Gli indirizzi `/open-data` e `dati.arera.it` rispondono 404 e connessione fallita.
- AGCOM, MIMIT, MASE: `agcom.it/dati-e-statistiche` risponde 404; non ho aperto fonti MIMIT e MASE. NON VERIFICATO. Fuori dal tempo dedicato.
- MIM scuole per provincia (numero di scuole): assoluto, e senza denominatore pulito. Scartato.
- Dati provinciali di Bolzano, Trento e Aosta per alunni e docenti: esistono solo come anagrafica (`SCUANAAUTSTAT`, `SCUANAAUTPAR`, "province autonome equiparate"), non come alunni/docenti. Per questo i candidati MIM 1-3 coprono 104 province, non 107.

## Avvertenze generali per l'integrazione

- Tre territori mancano in tutti i dati MIM scuola (AO, BZ, TN): la scheda regione/provincia di quei tre non avrebbe valore e va dichiarato in `docs/` come per gli altri indicatori parziali.
- "Sud Sardegna" in tutti i dati MIM e MUR del 2024/25: il raccordo con i 107 codici del repo va controllato (la riforma 2025 ha reintrodotto province sarde).
- I CSV MIM usano virgola, UTF-8, un file per anno scolastico (nome con ANNOSCOLASTICO e data di pubblicazione, es. `...20242520250831`): lo scarico deve scoprire il nome dall'elenco della pagina `?area=...`, non dedurlo.
- Il portale MIM risponde 200 senza login con un normale User-Agent; con `curl` senza User-Agent non l'ho provato.

---

# Ricerca fonti non Istat-SDMX: sicurezza, cultura, turismo, mobilita'

Data della ricerca: 1 ottobre 2026. File scaricati in `lavoro/parti/fonti_sicurezza/`.
Esito: 3 candidati verificati aprendo e scaricando il file; il resto scartato o non verificato. Niente e' stato inventato.

## Candidati verificati

### 1. Reddito imponibile medio IRPEF per contribuente (provincia)
1. Nome: "Reddito imponibile IRPEF medio per contribuente". Istituzione: Ministero dell'Economia e delle Finanze, Dipartimento delle Finanze.
2. Dato: https://www1.finanze.gov.it/finanze/analisi_stat/public/v_4_0_0/contenuti/Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_2024.zip (scaricato, CSV a punto e virgola, latin-1, 7897 righe di comuni). Pagina di metodo e catalogo: https://www1.finanze.gov.it/finanze/analisi_stat/public/index.php?opendata=yes . Licenza: la pagina riporta "Tipo licenza" con il logo e il link http://creativecommons.org/licenses/by/3.0/it/ (CC BY 3.0 IT). Nessuna frase estesa letta, solo logo e link. Non ho trovato una nota metodologica scaricabile separata (non verificato).
3. Livello: comune, con sigla provincia e codice Istat regione. Aggregando per sigla: 107 province (codici sigla, incluso SU, BZ, TN, AO). Le 20 regioni si ottengono sommando; TAA = BZ+TN. Righe con provincia "0" (non attribuibili) da escludere.
4. Anni: file comunale dal 2000 (zip CSV_2000 presente) all'anno d'imposta 2024 (dichiarazioni 2025, aggiornamento del 23 aprile 2026; il file comunale ha data 14/04/2026). Annuale. Ultimo >= 2023: si'.
5. Unita': euro. Relativo (ammontare / numero di dichiaranti con imponibile). Colonne: "Reddito imponibile - Ammontare in euro" / "Reddito imponibile - Frequenza".
6. Verso: higher_better (con cautela: e' reddito dichiarato, non patrimonio).
7. Doppione: grep nel catalogo su reddito/imponibil/contribuent/irpef: solo reddito disponibile, primario, netto familiare (Istat/BES/Banca d'Italia), nessun imponibile IRPEF. Nuovo.
8. Esempio (calcolato dal file, anno d'imposta 2024, media su dichiaranti con imponibile): alto Milano (MI) 33.635 euro; basso Crotone (KR) 17.765 euro; mediano Sondrio (SO) 23.822 euro. Variante su tutti i contribuenti: MI 31.806, KR 16.952, MS 22.731.
9. Integrazione: bassa/media. Un solo download per anno, una riga per comune, aggregazione per sigla. Attenzione: domicilio fiscale; decimali con virgola; le sigle vanno mappate sui codici provincia del repo. Rischio: nome non Istat, etichetta "Ministero dell'Economia e delle Finanze, Dipartimento delle Finanze" (sources.py).

### 2. Quota di contribuenti con reddito complessivo oltre 55.000 euro (provincia)
Stesso file del n. 1 (stessa licenza, metodo, copertura, anni).
1. Nome: "Contribuenti con reddito complessivo oltre 55.000 euro". MEF Dipartimento delle Finanze.
5. Percentuale: somma delle frequenze delle classi 55-75k, 75-120k, oltre 120k diviso "Numero contribuenti". Relativo.
6. Verso: contextual (misura di alta fascia, non un giudizio).
7. Doppione: nel catalogo ci sono Gini e s80/s20 (Istat), nessuna quota di alti redditi IRPEF. Nuovo.
8. Esempio calcolato (anno d'imposta 2024): alto Milano 11,4%; basso Sud Sardegna 1,9%; mediano Palermo 4,8%.
9. Integrazione: come il n. 1, e' un derivato dalle stesse colonne. Candidato a basso costo aggiuntivo.

### 3. Autovetture ogni 100 abitanti (tasso di motorizzazione, provincia)
1. Nome: "Autovetture per 100 abitanti". Istituzione: Automobile Club d'Italia (ACI).
2. Dato: https://aci.gov.it/app/uploads/2025/11/Veicoli-su-popolazione-Indicatori-2024.xlsx (scaricato; fogli "Prov - AV su Pop", "Prov - MC su Pop", "Prov - Veic su Pop" e i tre dei capoluoghi). Parco provinciale in conteggi: https://aci.gov.it/app/uploads/2026/06/Autoritratto2025_Parco_veicolare.zip (scaricato, contiene Parco_veicolare_2025.xlsx, 45 fogli, province per categoria, uso, alimentazione). Pagina: https://aci.gov.it/attivita-e-progetti/studi-e-ricerche/autoritratto/ e note: https://aci.gov.it/app/uploads/2025/06/Note_metodologiche_e_considerazioni_2023.pdf (scaricata, non letta per intero). Licenza: sulla pagina Open Data ACI "I dati statistici della presente sezione sono liberamente fruibili da chiunque nel rispetto dei termini previsti dalla licenza di utilizzo Creative Commons CC-BY 4.0"; il piede delle pagine ACI riporta "CC BY 4.0". Rimane da confermare che valga per la sezione Autoritratto (il footer si'; la frase e' sulla pagina open-data).
3. Livello: 107 province nel foglio indicatori (128 voci = 107 province + 21 totali regionali/macroarea; verificato via conteggio, non elencati i codici uno a uno). Nomi provincia, non sigle. Regioni: righe "Totale ..." (TRENTINO come unica voce, quindi TAA gia' fatta).
4. Anni: indicatori 2024 (un solo anno nel file); i conteggi del parco veicolare sono annuali dal 2002 al 2025 (Autoritratto). Quindi serie lunga ricostruibile dividendo per la popolazione Istat. Ultimo 2024 (indicatore) o 2025 (conteggi), >= 2023.
5. Unita': autovetture ogni 100 abitanti. Relativo.
6. Verso: contextual. Distorsioni note: province sede di flotte di noleggio (es. Firenze, Isernia).
7. Doppione: grep motorizz/autovettur/veicol/immatric nel catalogo: nessuna corrispondenza (solo rete stradale, TPL). Nuovo.
8. Esempio dal foglio "Prov - AV su Pop" (2024): alto Firenze 87,66 (probabile effetto noleggio); basso Genova 51,11; mediano Vicenza 70,63. Altri: Milano 57,11, Trieste 57,93.
9. Integrazione: media. Foglio non tabellare (cinque colonne affiancate nome/valore, righe "Totale ..."); meglio usare Parco_veicolare_2025.xlsx foglio "1 Provincia categoria" (regione/provincia/autovetture, formato tidy) e dividere per popolazione Istat gia' nel repo. Nessun codice provincia, solo nomi (da mappare). Cautela: Sud Sardegna e riordino delle province sarde.
Nota: le auto elettriche per provincia NON sono nel file verificato (il foglio alimentazione e' nazionale). Non verificato se altre pubblicazioni ACI le diano per provincia.

## Scartati e non verificati
- Delitti denunciati per provincia (Ministero dell'Interno, UCS, scheda INT 00062): dati.interno.gov.it non risponde da qui (timeout). Gli URL di ucs.interno.gov.it trovati dalla ricerca reindirizzano alla home (sito riscritto); nessun file scaricabile raggiunto. Non verificato. In ogni caso il catalogo copre gia' furti, rapine, denunce di rapina, microcriminalita', criminalita' minorile e organizzata, delitti mortali: forte rischio doppione. Non proposto.
- Musei e visitatori (Ministero della Cultura, statistica.cultura.gov.it): pubblicato il 12/05/2025 il rilevamento 2024 sui visitatori di musei statali. Sito raggiunto (HTTP 200), file e licenza non aperti. Scartato come doppione del catalogo (diversi "Indice di domanda culturale dei musei...", "Grado di promozione dell'offerta culturale...") e perche' sono assoluti per singolo istituto, non relativi per provincia. Non verificato oltre.
- Turismo presenze/arrivi per provincia (Istat): la fonte primaria passa da esploradati, esclusa dalla richiesta. Non cercata altra via ufficiale. Il catalogo ha gia' "Tasso di turisticita'" e "Turismo nei mesi non estivi".
- Incidentalita' stradale ACI-Istat per provincia: le pagine ACI portano le tavole (ultima con link diretto 2023: Report_incidenti_stradali_2023_IT.pdf, Indice_tavole_2023.pdf), ma non ho aperto una tavola provinciale ne' letto la licenza. Il catalogo contiene gia' "Mortalita' per incidenti stradali" e "Mortalita' stradale in ambito extraurbano". Non verificato, probabile doppione.
- Auto elettriche per abitante: vedi sopra, nessun dato provinciale trovato.
- MIT, Motorizzazione, INPS osservatori, Unioncamere/Infocamere, OMI: non verificati. Il link a INPS testato ha dato 404, MIT nessuna risposta, camcom.gov.it raggiungibile ma non esplorato. OMI scartata in partenza (prezzi immobili non richiesti se non relativi).
- File ACI "Circolante_Copert_2025.xlsx" e "Circolante_FTS_Autovetture_2025.xlsx": scaricati nel pacchetto ACI ma non analizzati a fondo (fogli per area e regione, marca/tipo); non servono.

## Raccomandazione
Integrare per primi n. 1 e n. 2 (stesso file MEF, costo minimo, fonte ufficiale non Istat, 107 province, 2024). Il n. 3 e' valido ma richiede un abbinamento per nome provincia e dichiarare l'effetto noleggio. Sicurezza e turismo: nessun candidato nuovo verificato in questa passata.
