# Fonti esterne aperte e verificate (08/10/2026)

Tutte aperte con `curl` (HTTP 200) e lette in locale con pypdf/openpyxl il 08/10/2026. Citazioni letterali copiate dal testo estratto.

## 1. Istat, Bes dei territori 2025, report regionale Calabria
- URL: https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Calabria.pdf
- HTTP 200, application/pdf, 688.351 byte, 18 pagine. Data: `last-modified` 04/12/2025, creazione PDF 03/12/2025.
- Anno del dato: 2023 (ultimo anno dell'indicatore).
- Citazione: «nella regione l'incidenza di pensionati con reddito pensionistico di basso importo (meno di 500 euro mensili): nel 2023 sono il 14,0 per cento del totale, 5,1 punti percentuali in più che in Italia. A Crotone (16,9 per cento) l'indicatore è quasi il doppio che in Italia (8,9).»
- Tavola 4, riga Italia: «Pensionati con reddito pensionistico di basso importo» 2023 = 8,9. Riga Mezzogiorno 12,8.
- Limite d'uso: il report dice anche che «Questi due indicatori evidenziano anche i divari provinciali più ampi». Non spiega le cause. Il valore provinciale di Bolzano non è in questo report (vedi la fonte 2).

## 2. Istat, Bes dei territori 2025, appendice statistica (foglio Glossario e foglio Dominio 04) e report Trentino-Alto Adige
- URL: https://www.istat.it/wp-content/uploads/2025/12/Appendice_Sicilia_2025.xlsx (HTTP 200, 244.579 byte)
- URL: https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Trentino-Alto-Adige.pdf (HTTP 200)
- Anno del dato: 2019 e 2023.
- Glossario, definizione: «Percentuale di pensionati che percepiscono un reddito pensionistico lordo mensile inferiore a 500 euro sul totale dei pensionati.» Fonte indicata: «Istat | Statistiche della previdenza e dell'assistenza sociale». Nell'edizione 2025 il codice è `04-04` (nel nostro catalogo `04BEC006P`, edizione 2024, stessa definizione in `data/definitions/federated.csv`).
- Foglio Dominio 04, riga Italia: 10,4 (2019), 8,9 (2023), differenza -1,5. Riga Mezzogiorno: 14,8, 12,8, -2. Italia, importo medio annuo pro-capite dei redditi pensionistici: 19.110,7 (2019), 21.736,8 (2023).
- Report Trentino-Alto Adige: «la quota di pensionati con reddito pensionistico di basso importo è pari al 5,2 per cento (3,7 punti in meno dell'Italia; -2,6 rispetto al 2019).»
- Limite d'uso: il foglio ha un nome che dice Sicilia ma contiene le tavole di tutta Italia e dei territori della regione (la stessa appendice è usata già nella scheda `bes__04BEC002P`). Le cifre provinciali del CSV di sito coincidono con la Tavola 4 della Calabria (Crotone 16,9; Cosenza 14,5; Reggio di Calabria 14,0; Vibo Valentia 13,4; Catanzaro 12,1).

## 3. INPS, Osservatorio statistico «Pensioni - Vigenti e Liquidate», pensioni vigenti all'1.1.2026 e liquidate nel 2025
- URL: https://servizi2.inps.it/servizi/osservatoristatistici/api/getAllegato/?idAllegato=1037
- HTTP 200, PDF, 737.790 byte, 35 pagine. Data: file creato il 23/03/2026. Nota metodologica: `idAllegato=1036`.
- Anno del dato: **1 gennaio 2026** (stock). Non è il 2023: serve come contesto, non per confermare il numero Bes.
- Citazioni: «Al 1° gennaio 2026 le pensioni vigenti in Italia sono 21.257.999» e «delle 9.704.016 pensioni con importo inferiore a 750 euro, solo il 42,2% (4.091.750) beneficia di prestazioni collegate a bassi requisiti reddituali, quali integrazione al minimo, maggiorazioni sociali, pensioni e assegni sociali e pensioni di invalidità civile.»
- Citazione sul limite: «la forte concentrazione delle pensioni nelle classi di importo più basse non rappresenta necessariamente una misura diretta della condizione economica dei pensionati, poiché una parte di essi può percepire più prestazioni pensionistiche o disporre di ulteriori fonti di reddito.»
- Unità: **pensioni, non pensionati**. Soglia: 750 euro, non 500. Il documento non pubblica una quota sotto 500 euro (ho cercato «500» nel testo: non c'è come classe).
- Limite d'uso: serve per spiegare che cosa non dice un reddito pensionistico basso (più pensioni per persona, integrazione al minimo, reversibilità). Non si cita come prova del 16,9% di Crotone.

## 4. Istat, Annuario statistico italiano 2025, capitolo 5 Protezione sociale
- URL: https://www.istat.it/storage/ASI/2025/capitoli/C05.pdf
- HTTP 200, 421.488 byte, 10 pagine. Data: `last-modified` 17/12/2025.
- Anno del dato: 2023.
- Citazione: «Nel 2023, in totale (comparto pubblico e privato) sono stati erogati circa 22,9 milioni di trattamenti pensionistici (+0,6 per cento rispetto al 2022) per una spesa pari a 347.031 milioni di euro (+7,7 per cento) e con un importo medio annuo di 15.141 euro.» E: «quelli più bassi in Basilicata (12.915) e Calabria (12.255 euro).»
- Limite d'uso: unità = trattamenti (pensioni), non pensionati, per regione di erogazione. Fonte: Istat, Archivio statistico dei trattamenti pensionistici. Contesto, non il nostro indicatore.

## Non trovato / non aperto
- Pagina Istat «Bes dei territori edizione 2025» (https://www.istat.it/notizia/bes-dei-territori-edizione-2025/): HTTP 200, ma non ho verificato in pagina la data di pubblicazione. Non la elenco come fonte del dato.
- Una pubblicazione Istat «Condizioni di vita dei pensionati» sul 2023: **non esiste**. L'ultima è «anni 2020-2021», 07/12/2022 (https://www.istat.it/comunicato-stampa/condizioni-di-vita-dei-pensionati-anni-2020-2021/, non aperta da me, vista solo nell'elenco della pagina tag Istat).
- INPS: tabella con quota di pensioni (o di pensionati) sotto i 500 euro: non trovata. Osservatorio sul Casellario dei pensionati con classi di importo per pensionato: non trovato.
- Corte dei conti e Banca d'Italia: non cercate a fondo, nessuna fonte aperta. Non le elenco.
- Spiegazione ufficiale del calo 2022 -> 2023 (rivalutazione delle pensioni a gennaio 2023 con soglia di 500 euro non indicizzata): **non verificata** in nessuna fonte aperta. È un'ipotesi del redattore, non va scritta come fatto.

## Che cosa NON dice l'indicatore
- Misura i **pensionati**, ma con il reddito **pensionistico lordo mensile** (somma delle pensioni percepite, per definizione Istat «reddito pensionistico»). Non è il reddito della persona né della famiglia: chi ha una pensione bassa può avere altri redditi, un coniuge con pensione più alta, una casa di proprietà.
- Soglia fissa di 500 euro lordi mensili, in euro correnti: non è una soglia di povertà e non segue l'inflazione.
- Pensione ≠ reddito familiare. Integrazione al minimo, maggiorazioni sociali, pensioni sociali, invalidità civile e reversibilità: la fonte INPS dice che il 42,2% delle pensioni sotto 750 euro (1.1.2026) è collegato a requisiti reddituali bassi. Se queste prestazioni siano contate nel «reddito pensionistico» della definizione Istat non è chiarito dal glossario: **non affermarlo**.
- Non dice quanti sono: tasso, non persone. Territorio = provincia, ma non è documentato nel glossario se sia di residenza o di erogazione: **non verificato**, da dichiarare come limite.
