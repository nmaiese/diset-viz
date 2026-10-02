# RICERCA R2a: economia, imprese, infrastrutture, mobilità, energia

Data ricerca: 1 ottobre 2026. Solo ricerca, nessuna modifica al codice. Valori letti dai file scaricati, salvo dove scritto "non verificato".
Doppioni cercati per parola chiave in `Assoluti_Regione.csv`, `bes_regione_manifest.csv`, `province_manifest.csv`, `multiscopo_regione_manifest.csv`, `external_indicator_manifest.csv`.

Riepilogo: 3 candidati puliti e verificati (1 e 2 ACI, 3 AGCOM), 1 buono ma con licenza e download da chiarire (4 Movimprese), 2 deboli e non verificati del tutto (5 Terna, 6 Banca d'Italia). Non arrivo a 10: le fonti del flusso R2a che arrivano al 2025 e sono scaricabili e relative sono poche, il resto si ferma al 2024.

---

## CANDIDATI (ultimo anno >= 2025)

### 1. Vetustà del parco auto: quota di autovetture immatricolate fino al 2009
- Pubblica: Automobile Club d'Italia (ACI), Autoritratto 2025.
- Dato: https://aci.gov.it/app/uploads/2026/06/Autoritratto2025_Parco_veicolare.zip (8 MB, contiene `Parco_veicolare_2025.xlsx`, foglio "28 AV Provincia anno"). Metodo e pagina: https://aci.gov.it/attivita-e-progetti/studi-e-ricerche/autoritratto/.
- Licenza: pagina Open Data ACI, letta: "liberamente fruibili da chiunque nel rispetto dei termini previsti dalla licenza di utilizzo Creative Commons CC-BY 4.0" (https://aci.gov.it/attivita-e-progetti/studi-e-ricerche/open-data/).
- Territorio: 107 province su 107 (nomi ACI in maiuscolo, join per nome o sigla; "Totale" e aggregati di ripartizione da scartare). Regioni: sommando le province, 20.
- Anni: stock al 31/12/2025 (zip del 23/06/2026). Frequenza annuale. Serie storica precedente per anno: edizioni Autoritratto passate (non scaricate). Ultimo anno 2025: OK.
- Unità: % su autovetture della provincia (relativo). Calcolo: colonna "FINO AL 2009" / "Totale" del foglio.
- Verso: lower_better (parco più vecchio = più inquinante, meno sicuro). È una proxy, ma onesta; da dichiarare "contextual" se si vuole prudenza (redditi e territori montani incidono).
- Doppione: no. Cercato veicol, autovettur, parco, ecolog: in catalogo c'è solo "Dotazione di parcheggi di corrispondenza" (Istat). Nuovo.
- Esempio (calcolato dal foglio 28, 107 province): Trento 13,9% (basso), Biella 39,6% (medio, mediana), Catania 60,0% (alto).
- Integrazione: facile. XLSX con intestazione a 3 righe, nome provincia in colonna B, ultima colonna totale. Un solo anno per edizione: serie storica da ricostruire con le edizioni passate.

### 2. Autovetture a basse emissioni o alimentazione alternativa (quota non benzina/gasolio)
- Pubblica: ACI, Autoritratto 2025. Stesso file, fogli "36 AVAltre Provincia cilindrata" (autovetture con alimentazione diversa da benzina e gasolio) e "27 AV Provincia cilindrata" (totale).
- Licenza, URL, anni: come il candidato 1.
- Territorio: 107 province.
- Unità: % su autovetture. Calcolo: totale foglio 36 / totale foglio 27.
- Verso: higher_better con cautela. Comprende ibride, GPL, metano, elettriche. Non misura l'elettrico puro (il dettaglio per alimentazione è solo nazionale nel foglio 2, per provincia manca): va chiamata "alimentazione alternativa a benzina e gasolio", mai "auto green".
- Doppione: no (nessuna misura sul parco in catalogo).
- Esempio: Nuoro 5,5% (basso), Siena 18,0% (medio), Firenze 34,6% (alto).
- Integrazione: facile come il candidato 1. Attenzione: la quota alta di Firenze e di altre province dipende anche dalle flotte del noleggio con sede lì, non solo dai residenti. Dichiararlo nel metodo.

### 3. Copertura della rete in fibra FTTH (famiglie raggiunte)
- Pubblica: Autorità per le garanzie nelle comunicazioni (AGCOM), Broadband Map.
- Dato: https://geo.agcom.it/reportistica/doc/RapportoAggiornamentoBBmap_4Q25vs4Q24_r260119.pdf (444 pagine, rilevazione 8 gennaio 2026, rev. 19 gennaio 2026). Portale con i file Excel e le mappe: https://geo.agcom.it/ (sezione "Reportistica & Open Maps"). Il link diretto all'Excel non l'ho trovato: **non verificato**; nel PDF c'è tutto ma a precisione intera (province) o a due decimali (regioni).
- Licenza, citata dal PDF (par. 4): "Tutti i dati del Portale BBMap sono rilasciati sotto licenza Creative Commons Attribuzione 4.0 Internazionale (CC BY 4.0)". Obbligo di citare paternità e indirizzo del portale.
- Territorio: 20 regioni (Trentino-Alto Adige presente come unica regione nella sintesi, 62,86%), 107 province nel capitolo 7 del PDF, comuni nei capitoli successivi.
- Anni: istantanee trimestrali, la più recente del 4° trimestre 2025 (e altre uscite dopo: verificare il rapporto 1T/2T 2026 prima di integrare). Confronto con 10/01/2025 incluso. Ultimo anno 2025: OK.
- Unità: % di famiglie raggiunte dalla rete FTTH (relativo).
- Verso: higher_better. Onesto: la disponibilità della fibra è un servizio.
- Doppione: **parziale, da decidere**. In catalogo ci sono "Copertura della rete fissa di accesso ultra veloce a internet" (BES 12SER020, Istat, provinciale) e "Copertura con banda ultralarga ad almeno 30 Mbps" (Istat, regionale). La FTTH è una tecnologia più stringente e con dati più recenti (l'Istat arriva al 2023 o 2024 per quelle), quindi è una misura diversa, ma il lettore vedrà due "copertura" accanto. Raccomandazione: introdurla con nome "Famiglie raggiunte dalla fibra FTTH" e collegarla alle altre due.
- Esempio, regioni (4T 2025): Valle d'Aosta 58,63% (basso), Piemonte 73,20% (medio), Sicilia 89,06% (alto). Italia 77,19%.
- Esempio, province (dal capitolo 7, intero): Bolzano 37% (basso), Massa Carrara 74% (medio), Palermo 95% (alto). Nota del PDF sulle province autonome: i dati di Bolzano e Trento hanno una lacuna di rilevazione, quindi prima di pubblicare Bolzano leggere la sezione di metodo (righe iniziali del PDF, "Note metodologiche generali").
- Integrazione: media. Province estraibili dal PDF con una regex ("La provincia di X ha una copertura FTTH che raggiunge il N%"): 107 risultati, ma intero arrotondato. Per avere i decimali serve l'Excel del portale.

### 4. Tasso di crescita delle imprese per provincia (Movimprese)
- Pubblica: InfoCamere per Unioncamere, Movimprese. Pagina dati e metodo: https://www.infocamere.it/movimprese. Comunicato 2025 (23/01/2026): https://www.unioncamere.gov.it/comunicazione/comunicati-stampa/imprese-nel-2025-la-crescita-tocca-il-1-saldo-positivo-di-57mila-unita.
- Dato: il modulo "Scarica CSV" della pagina (anno, periodo, regione, provincia, settore). Il CSV sta dietro un reCAPTCHA (letto nello script `downloadCsv.js`): **non scaricabile da script, non ho potuto leggere i valori dal CSV**. Va scaricato a mano una volta per anno e committato.
- Licenza: condizioni di utilizzo (PDF 30/04/2025), lette: "L'uso e la diffusione delle informazioni contenute nei file scaricabili dal presente sito sono consentiti previa citazione della fonte." Non è una CC né una IODL: **licenza non standard, ambigua**. Chiedere conferma a movimprese@infocamere.it prima di pubblicare tabelle.
- Territorio: province (107) e regioni, serie dal 1° trimestre 2000. Nota: le province possono cambiare codice (il form filtra per validità), controllare Sud Sardegna e le province sarde.
- Anni: 2025 annuale, ultimo trimestre il 2° 2026 (la pagina cita il 2° trimestre 2026, saldo di quasi 33 mila imprese, dal 1° trimestre 2026 classificazione ATECO 2025). Ultimo anno >= 2025: OK.
- Unità: tasso di crescita % (iscrizioni meno cessazioni non d'ufficio, su imprese registrate a inizio periodo). Relativo.
- Verso: higher_better. Con cautela: iscrizioni di comodo e cancellazioni d'ufficio sfalsano. Dichiarare "cessazioni non d'ufficio".
- Doppione: **parziale**. In catalogo c'è "Tasso di natalità delle imprese" (Istat, regionale, id 54): la natalità non coincide con il saldo, ma si somiglia. Il tasso di crescita e quello di mortalità sono nuovi, e provinciali.
- Esempio, dal comunicato (non dal CSV): Roma +2,54% (alto), Milano +2,37%, Siracusa +2,11%; Italia +0,96% (saldo +56.599). Provincia bassa e provincia media: **non verificato** (non ho potuto leggere il CSV né una tabella provinciale).
- Integrazione: media-alta (CSV manuale, captcha, licenza da chiarire).

### 5. Elettricità: consumi per abitante, regione (Terna)
- Pubblica: Terna (gestore della rete di trasmissione elettrica nazionale), Dati statistici sull'energia elettrica in Italia, edizione 2025 (dati 2025).
- Dato verificato: capitolo "Produzione 2025", https://download.terna.it/terna/05_PRODUZIONE_8df127663b30d60.pdf (24 pagine, tabella 26 "Produzione di energia elettrica in Italia secondo regione", GWh 2024 e 2025). Il capitolo dei **consumi** e quello "Elettricità nelle regioni" del 2025: **non trovati, non verificati** (ho trovato solo l'edizione 2024: https://download.terna.it/terna/06_CONSUMI_8de38d06c930a94.pdf). Portale dati: https://dati.terna.it/en/load/statistical-data (consumi per regione e provincia, "Export data"; non verificato che arrivi al 2025).
- Licenza: **non trovata** né sul portale né nei PDF. Non verificato. SISTAN lo elenca come prodotto statistico ufficiale (https://www.sistan.it/news/prodotto/dati-statistici-sullenergia-elettrica-italia).
- Territorio: regioni (20) e province (consumi per provincia nel volume).
- Anni: serie storica lunga; 2025 presente almeno nella produzione.
- Unità: GWh assoluti. Diventa relativo solo con la popolazione Istat (kWh per abitante): join con la popolazione già in repo.
- Verso: contextual (consumo alto non è buono né cattivo: un'industria energivora lo gonfia). Non adatto a un punteggio.
- Doppione: **forte**. In catalogo ci sono già "Consumi di energia elettrica coperti da fonti rinnovabili" (Istat, % regionale), i consumi per settore (agricoltura, industria, terziario, PA, illuminazione) e "Energia prodotta da fonti rinnovabili". I consumi pro capite totali non ci sono, ma portano poco.
- Esempio (tabella 26 del PDF 2025, produzione lorda totale in GWh, assoluti, 2025): Lombardia 53.854,4; Piemonte 27.041,2; Valle d'Aosta 3.415,3. **Non sono consumi e non sono relativi**: servono solo a dimostrare che la tabella 2025 esiste.
- Raccomandazione: rimandare finché non si trova la licenza e il file consumi 2025.

### 6. Prestiti bancari e depositi per provincia (Banca d'Italia) , solo parzialmente verificato
- Pubblica: Banca d'Italia, "Banche e istituzioni finanziarie: finanziamenti e raccolta per settori e territori", edizione del 30 settembre 2026 (II trimestre 2026): https://www.bancaditalia.it/pubblicazioni/finanziamenti-raccolta/2026-finanziamenti-raccolta/statistiche_STAFINRA_20260930.pdf. Elenco delle tavole della Base dati statistica (BDS): http://www.bancaditalia.it/statistiche/basi-dati/bds/STAFINRA_tavole_BDS_it.pdf. Esempio di tavola provinciale: TFR50232 "Prestiti (esclusi PCT) per provincia, settore e attività economica della clientela". Nota metodologica: https://www.bancaditalia.it/pubblicazioni/metodi-e-fonti-note/metodi-note-2026/STAFINRA_note-met_20260908.pdf.
- Territorio: province e regioni. Anni fino al 2026 (trimestrale). Ultimo anno >= 2025: OK.
- Licenza: la pagina copyright dice che gli open data Banca d'Italia su dati.gov.it sono CC BY 4.0, ma per le statistiche vale la condizione SEBC "citare la fonte, non modificare il contenuto": **ambigua**, perché un rapporto prestiti/abitante è una rielaborazione.
- Unità: euro di consistenze (assoluti). Un indicatore relativo onesto richiede un rapporto: prestiti alle famiglie per abitante, oppure tasso di decadimento (che c'è già solo come BES 04BEC009P, "Tasso di ingresso in sofferenza dei prestiti bancari alle famiglie", provinciale Istat).
- Esempio reale: **non verificato**. Non sono riuscito a interrogare la BDS da script; i valori non li ho letti.
- Doppione: parziale (sofferenze famiglie e "Impieghi bancari delle imprese non finanziarie sul PIL", regionale, già presenti).
- Raccomandazione: non procedere finché non c'è un'API BDS verificata e una conferma sulla licenza.

---

## SCARTATI

| Fonte | Perché |
| --- | --- |
| ACI "Veicoli su popolazione, Indicatori" (provincia, auto ogni 1000 abitanti, età media, Euro) | File `Veicoli-su-popolazione-Indicatori-2024.xlsx` con dati al 31/12/2024: si ferma al 2024. La motorizzazione si può ricalcolare dal parco 2025 (autovetture, foglio 1) diviso popolazione Istat, ma è una derivazione nostra, non il dato ACI: vedi nota in fondo. |
| ACI-Istat incidenti stradali per provincia | Provinciale ultimo disponibile 2024 (file `Localizzazione-Strade-Provinciali_2024.xlsx`, tavole 2024 uscite a ottobre 2025). Il report 2025 (luglio 2026) c'è, ma il dettaglio provinciale 2025 non è ancora scaricabile. Da rivedere a ottobre 2026. In catalogo esistono già "Mortalità per incidenti stradali (15-34 anni)" e "Mortalità stradale in ambito extraurbano". |
| GSE fotovoltaico per abitante | Rapporto statistico 2024 (dati al 31/12/2024): si ferma al 2024. Il rapporto 2025 non risulta uscito (la serie esce a settembre dell'anno dopo). Dati letti dai risultati di ricerca, non aperti. |
| INPS dipendenti, retribuzione media provinciale | Ultima rilevazione provinciale 2024 (17.731.002 dipendenti con almeno una giornata retribuita nell'anno 2024, dai risultati di ricerca); non verificato che esista il 2025. Da rivedere. |
| ANAC appalti (CIG anno 2025) | Il portale https://dati.anticorruzione.it/opendata/dataset/cig-2025 ha risposto "The requested URL was rejected" al mio client: **non verificato**. Dai risultati di ricerca la licenza è CC BY-SA 4.0 (share-alike: vincolante per le opere derivate, da valutare). I dati sono contratti singoli (assoluti), per avere un indicatore relativo serve una derivazione (importo per abitante, quota gare sotto soglia, quota affidamenti diretti). Non proposto. |
| Terna, produzione per regione | Assoluti (GWh), premiano la taglia, e doppione delle rinnovabili Istat. |
| Unioncamere imprenditoria femminile/giovanile | Esistono i rapporti, ma non ho trovato un file provinciale scaricabile: **non verificato**. Da cercare nel CSV Movimprese (se contiene le classi) o nei rapporti di Unioncamere. |

## COSA NON HO POTUTO FARE (dichiarato)
- Movimprese: CSV dietro captcha, valori medio e basso non letti; licenza non standard.
- AGCOM: link diretto agli Excel non trovato, valori province letti dal PDF.
- Terna: capitolo consumi 2025 e licenza non trovati.
- Banca d'Italia: nessun valore letto.
- ACI: il rapporto auto per 1000 abitanti non l'ho calcolato (mancava la popolazione al 1° gennaio 2026 nel mio perimetro); le tre quote dei candidati 1 e 2 sono invece calcolate dal file.

## RACCOMANDAZIONE
1. Integrare subito i candidati 1, 2, 3 (ACI vetustà, ACI alimentazione alternativa, AGCOM FTTH): licenza CC BY 4.0 chiara, 107 province, 2025, relativi, scaricabili.
2. Movimprese (4): alto valore (tasso di crescita provinciale, mortalità), ma prima conferma di licenza e un download manuale.
3. Terna e Banca d'Italia (5, 6): non ora.
4. Ripassare a ottobre 2026 per incidenti stradali provinciali 2025 e per l'edizione GSE 2025.
