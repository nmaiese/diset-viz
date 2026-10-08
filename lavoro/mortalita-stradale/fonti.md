# Fonti esterne aperte e verificate: mortalità per incidenti stradali 15-34 anni (`bes:01SAL005`), 08/10/2026

Tutte aperte con `curl -A DivarioCheck/1.0` (HTTP 200) e lette in locale (pypdf, openpyxl) l'8 ottobre 2026. Le citazioni sono copiate dal testo estratto. Dove il PDF spezza le righe ho unito le righe senza cambiare le parole.

## 1. Istat, Appendice statistica (Metadati.xlsx), Bes aggiornamento intermedio 2026: definizione dell'indicatore e fonte primaria
- URL: https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip (HTTP 200, 1.789.151 byte, `last-modified` 25/05/2026). Dentro: `Metadati.xlsx`, foglio Metadati, codice `01SAL005`.
- Anno del dato: serie 2004-2024 (ultimo anno 2024, come nel CSV del sito).
- Citazione, definizione: «Tassi di mortalità per incidenti stradali standardizzati con la popolazione europea al 2013 all'interno della classe di età 15-34 anni, per 10.000 residenti.»
- Citazione, fonte indicata: «Istat - Per i decessi: Rilevazione degli incidenti stradali con lesioni alle persone. Per la popolazione: Rilevazione sulla Popolazione residente comunale per sesso, anno di nascita e stato civile».
- Che cosa dice sul denominatore: il tasso è calcolato dentro la classe 15-34 e standardizzato per età sulla popolazione europea 2013 (cioè pesa le età interne alla classe come in una popolazione tipo). Lettura del redattore: il denominatore sono i residenti di 15-34 anni, non il totale. Il testo del glossario non scrive la parola «15-34 anni residenti» in una frase sola: la lettura è la più naturale, ma è una lettura.
- Limite d'uso: il glossario non dice se i decessi siano attribuiti alla regione dell'incidente o alla regione di residenza della vittima. Non verificato (vedi «Non trovato»). Il CSV del sito (`Assoluti_BES_Regione.csv`, archivio «Benessere equo e sostenibile, aggiornamento intermedio 2026») ha un decimale e nessun intervallo di confidenza.

## 2. Istat, Bes dei territori 2025, report regionale Sardegna (Tavola 1, Dominio Salute)
- URL: https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Sardegna.pdf (HTTP 200, 705.457 byte, 18 pagine, `last-modified` 04/12/2025, PDF creato il 03/12/2025).
- Anno del dato: **2023** per questo indicatore (la colonna porta «2023»).
- Tavola 1, riga per riga, colonna «Mortalità per incidenti stradali (15-34 anni) (c)», 2023: Sassari 0,4, Nuoro 0,8, Cagliari 1,3, Oristano 0,0, Sud Sardegna 1,2, SARDEGNA 0,8, Mezzogiorno 0,6, Italia 0,6.
- Citazione, nota (c): «(c) Tassi standardizzati per 10.000 residenti». Fonte della tavola: «Istat, indicatori Bes dei territori, edizione 2025».
- Uso: unico valore **Italia** trovato (0,6 nel 2023) e conferma che Sardegna 2023 = 0,8 come nel nostro CSV. Mostra anche la scala dei decimali: Oristano 0,0 e Cagliari 1,3 nella stessa regione, nello stesso anno.
- Limite d'uso: valore nazionale e provinciali solo per il 2023. Per il 2024 **non ho trovato** un valore Italia per questo indicatore.

## 3. Istat, Incidenti stradali in Italia, anno 2024 (report e comunicato stampa)
- URL: https://www.istat.it/wp-content/uploads/2025/07/REPORT_INCIDENTI_STRADALI_2024.pdf (HTTP 200, 1.045.065 byte, 28 pagine, `last-modified` 24/07/2025). Pagina del comunicato: https://www.istat.it/comunicato-stampa/incidenti-stradali-in-italia-2024/ («Periodo di riferimento: 2024, Data pubblicazione: 24 Luglio 2025»).
- Anno del dato: 2024.
- Citazione: «Il numero di morti in incidenti stradali ammonta a 3.030 (-0,3% rispetto al 2023), quello dei feriti a 233.853 (+4,1%), per un totale di 173.364 incidenti stradali (+4,1%).»
- Prospetto 3, morti (entro 30 giorni) per classe di età, 2024: 15-17 anni 80, 18-19 anni 78, 20-24 anni 252, 25-29 anni 203, 30-34 anni 160. La somma delle cinque classi è 773 su 3.030 (25,5%): somma mia, non scritta dal report. Variazioni 2024/2023: 15-17 +56,9%, 18-19 -13,3%, 20-24 +13,0%, 25-29 +10,9%, 30-34 -3,0%.
- Citazione, tasso per età: «il tasso specifico di mortalità più elevato è nella classe 85-89 anni (103,8 ogni milione di abitanti) seguita da quella 20-24 anni (84,7 ogni milione di abitanti)».
- Anomalia del report da NON ripetere: il testo dice «per le classi di età 20-24 e 25-29 anni l'aumento è del +23,9% nel complesso», ma il suo stesso Prospetto 3 dà +13,0% e +10,9%, e il report 2025 parla di «un aumento del +12,1%» per quel 2024. Usare solo le cifre del Prospetto.
- Citazione sul metodo: il tasso di mortalità stradale è «numero di morti per incidente stradale nel corso dell'anno per milione, o 100mila abitanti», cioè morti diviso popolazione media residente. Il morto è tale «entro 30 giorni» dall'incidente.
- Limite d'uso: tassi **per milione, grezzi, per classi di 5 anni**. Non sono il nostro indicatore (per 10.000, standardizzato, classe 15-34). Servono solo a dire che nel 2024 i morti 20-29 anni aumentarono in Italia, non a confermare il valore di una regione.

## 4. Istat-ACI, Incidenti stradali in Italia, anno 2025 (report) e Nota ACI-Istat
- URL: https://www.istat.it/wp-content/uploads/2026/07/REPORT_INCIDENTI_STRADALI_2025.pdf (HTTP 200, 1.630.415 byte, 28 pagine, `last-modified` 24/07/2026). Nota ACI-Istat: https://www.istat.it/wp-content/uploads/2026/07/Nota-ACI-ISTAT-2025.pdf (HTTP 200, `last-modified` 24/07/2026). Comunicato: https://www.istat.it/comunicato-stampa/incidenti-stradali-in-italia-2025/ («Periodo di riferimento: 2025, Data pubblicazione: 24 Luglio 2026»).
- Anno del dato: **2025**, successivo all'ultimo anno del nostro indicatore (2024). Contesto, non conferma della serie Bes.
- Citazione: «Nel 2025 si registrano 2.868 vittime in incidenti stradali (-5,3% rispetto al 2024)».
- Prospetto 3, 2025: 20-24 anni 229 morti (-9,1% sul 2024), 25-29 anni 164 (-19,2%), 18-19 anni 87 (+11,5%), 15-17 anni 74 (-7,5%).
- Citazione: «Nel 2025 si registra una diminuzione delle vittime per le classi di età 20-24 (-9,1%) e 25-29 (-19,2%) anni che avevano rilevato, però, mediamente un aumento del +12,1%, nel 2024, rispetto all'anno precedente».
- Limite d'uso: conta i morti, non i tassi regionali per 15-34. Non dice che cosa farà il nostro indicatore nel 2025. Non si usa per prevedere.

## 5. Istat, Incidenti stradali in Sardegna, anno 2024 (focus regionale)
- URL: https://www.istat.it/wp-content/uploads/2025/12/focus-sardegna-2024.pdf (HTTP 200, 992.741 byte, 13 pagine, `last-modified` 16/12/2025). Elenco: https://www.istat.it/comunicato-territoriale/incidenti-stradali-a-livello-regionale-anno-2024/.
- Anno del dato: 2024.
- Citazione: «In Sardegna, nel 2024, si sono verificati 3.583 incidenti stradali, che hanno causato la morte di 113 persone e il ferimento di altre 4.908.» E: «Si rileva inoltre un incremento delle vittime (+2,7%), in controtendenza al lieve calo osservato a livello nazionale (-0,3%).»
- Prospetto 1, Sardegna: morti 113 nel 2024 e 110 nel 2023, tasso di mortalità 2024 7,2 (per 100.000, tutte le età), Italia 5,1.
- Citazione: «Il tasso di mortalità standardizzato è più alto per la classe di età 15-29 anni (15,8 per 100mila abitanti) e per quella 30-44 anni (7,9).»
- Uso: nel 2024 le vittime sarde di **tutte le età** passano da 110 a 113 mentre il nostro tasso 15-34 passa da 0,8 a 1,3. Lo dico come limite del dato (piccoli numeri), non come spiegazione.
- Limite d'uso: il 15,8 per 100.000 è una classe diversa (15-29) e un'altra unità. Non va messo accanto all'1,3 per 10.000 come se fosse lo stesso numero (15,8 per 100.000 sono 1,58 per 10.000, ma classe e standardizzazione sono altre).

## Non trovato / non aperto
- **Valore Italia 2024** dell'indicatore `01SAL005`: non trovato in nessun documento aperto. La media semplice delle 20 regioni (0,685) non è un valore nazionale e non va chiamata così.
- **Numero assoluto di morti 15-34 per regione**: non pubblicato nelle fonti che ho aperto per il 2024. Non so quante unità stiano dietro lo 0,4 o l'1,3. Il 773 nazionale (somma delle cinque classi di età) è l'unico conteggio 15-34 che ho.
- **Attribuzione territoriale dei decessi** (luogo dell'incidente o residenza della vittima) per questo indicatore: non trovata. Il report incidenti raccoglie i dati per luogo dell'incidente (rilevazione per comune e mese), ma non ho letto una riga che lo dica per la costruzione dell'indicatore Bes.
- **ACI**: la pagina https://www.aci.it/laci/studi-e-ricerche/dati-e-statistiche/incidenti-stradali.html (indicata in `note.md`) risponde **404**. Non la elenco come fonte. L'ACI compare nel brief solo come co-autore della Nota ACI-Istat (fonte 4).
- **Istat «cause di morte»** (https://www.istat.it/it/archivio/324303, indicata in `note.md`): non aperta, non elencata.
- Spiegazioni di causa per la geografia (strade, mobilità, trasporto pubblico, alcol, velocità): nessuna fonte aperta le collega a questo indicatore. La scheda attuale (`content/indicators/bes__01SAL005.md`) le scrive senza fonte: vedi i «Dati NON ammessi» nel brief.
- Confronto europeo sui 15-34: non cercato. Il report Istat cita ETSC per il totale (Italia 51 per milione, Ue27 45, anno 2024), che non si applica ai 15-34.
