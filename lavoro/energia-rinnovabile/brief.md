level: regione

# Brief scheda: Energia elettrica da fonti rinnovabili (`bes:10AMB016`)

Tipo di pezzo: scheda indicatore (non blog). Livello: regione, 20 regioni (esiste anche il livello provincia, 107 province, 2015-2023, fuori dal perimetro di questa scheda). Ultimo anno: 2024 (Istat, Bes, aggiornamento intermedio 2026, file del 25/05/2026). Dati: `numeri.md` con le correzioni di questo brief. Fonti: `fonti.md`. Lunghezza: 600-800 parole di prosa, lead compreso. Nessuna persona citata, nessun dato personale.

## Requisito del front matter
`level: regione`, `key: "bes:10AMB016"`, `vintage: 2024`, `fonti` con le fonti 1, 2 e 3 di `fonti.md` (la 4 no, vedi sotto), `h1`, `seo_title` ≤ 60 caratteri. La scheda attuale (`content/indicators/bes__10AMB016.md`) ha `fonti: []` e va riscritta, non ritoccata: dice che le quote oltre il 100% sono dovute «alle esportazioni» (nessuna fonte aperta lo dice per le regioni) e usa lo schema `quadro, limiti`.

## 1. Domanda del lettore
Quanta energia rinnovabile c'è, e dove? Chi cerca «energia rinnovabile» vuole sapere quanta parte di ciò che consumiamo viene da sole, vento e acqua, e quali regioni sono avanti. La scheda risponde solo per l'elettricità: quanta ne producono le fonti rinnovabili di una regione rispetto all'elettricità che quella regione consuma.

## 2. Tesi in una frase
Nel 2024 la produzione elettrica da fonti rinnovabili vale il 41,7% dei consumi elettrici interni lordi dell'Italia, ma va dal 12,4% della Liguria al 327,8% della Valle d'Aosta, e dal 2012 la ripartizione più alta è il Mezzogiorno, non il Nord. È un rapporto fra due quantità della stessa regione, non una graduatoria di impegno né di virtù.

## 3. Esempi territoriali (dati ricalcolati dal CSV, confermati su `indicatori_regione_sesso.xlsx` Istat)
1. **Valle d'Aosta** (327,8% nel 2024, prima in tutti i 21 anni): produce più di tre volte ciò che consuma. Nel 2023 il 98,6% della sua produzione rinnovabile era idrica (3.124,5 su 3.170,2 milioni di kWh, Terna via Regione VdA, fonte 3). Il valore oscilla molto da un anno all'altro: 213,9 nel 2022, 293,3 nel 2023, 327,8 nel 2024.
2. **Basilicata**: da 15,2% nel 2004 a 124,1% nel 2024, sopra il 100% dal 2019 (record 136,6 nel 2023). Nel 2023 il 74,7% della sua produzione rinnovabile era eolica (3.239,1 su 4.338,5). Dal 2004 la quota è moltiplicata per otto circa.
3. **Liguria**: ultima nel 2024 con 12,4%, ultima anche in quasi tutti gli anni dal 2007 (nel 2004 e nel 2006 era ultima la Sicilia, con 1,5 nel 2004). Ha comunque guadagnato 9 punti dal 2004 (3,4).

## 4. Risultato non ovvio e controllo dei contrari
**Risultato**: nel 2004 il Mezzogiorno aveva la quota più bassa (8,2%, contro 18,8% del Nord). Dal 2012 (30,2% contro 27,1%) è la ripartizione più alta, e nel 2024 sta a 51,3% contro 40,7% del Nord e 30,8% del Centro (Istat). Tutte le 20 regioni hanno oggi una quota più alta del 2004.

**Controllo dei contrari**:
- «Allora il Sud produce più rinnovabile del Nord.» **No, e va detto.** La quota è un rapporto con i consumi della stessa regione. In assoluto nel 2023 il Nord produce 57.007 milioni di kWh da fonti rinnovabili e il Mezzogiorno 43.082 (Terna via Regione VdA, tavola 12.13, anno 2023). Vale solo il confronto fra quote, mai «il Sud produce di più».
- «Sopra il 100% vuol dire che la regione esporta.» Non scriverlo come spiegazione. Istat dice solo: «Valori superiori a 100 sono dovuti alla produzione di energia superiore alla richiesta interna.» Dove vada l'energia non è documentato per regione.
- «Il valore sale e basta.» No: nazionale 37,4 (2020), 35,1 (2021), 30,7 (2022), 36,9 (2023), 41,7 (2024). Nessuna fonte aperta spiega il 2022. Il comunicato Terna dà +30,4% di idroelettrico nazionale nel 2024: è un fatto nazionale, non la causa dei +34,5 punti della Valle d'Aosta e dei +45,1 del Trentino-Alto Adige fra 2023 e 2024.
- «41,7 o 41,2?» Istat 41,7 (consumo interno lordo, con pompaggi), Terna 41,2 (copertura della domanda, provvisorio). Sono denominatori diversi, non un errore (fonte 2). La scheda usa il 41,7 Istat e può citare il 41,2 solo con la spiegazione.
- «Il Trentino-Alto Adige è una sola regione.» Per Istat sì: 186,3 nel 2024. Sono due province autonome: Bolzano 234,3 e Trento 143,4 (Istat, stesso file). Nel 2022 il Trentino-Alto Adige stava a 97,1, sotto il 100.

## 5. Dati ammessi
- Valori regionali 2004-2024 del CSV del sito (`bes:10AMB016`) e ordinali del sito a parità di valore.
- Italia e ripartizioni (Nord, Centro, Mezzogiorno) 2004 e 2024, Bolzano e Trento 2024: solo da Istat (fonte 1), attribuiti a Istat.
- Fonte 3 (Terna via Regione VdA, 2023): la composizione per fonte (Valle d'Aosta idrica, Basilicata eolica, Puglia eolico più fotovoltaico) e il confronto in assoluto Nord-Mezzogiorno. Anno 2023 e unità (milioni di kWh) sempre detti.
- Fonte 2 (Terna 16/01/2025): il 41,2% nazionale con la sua spiegazione, e il +30,4% idroelettrico come dato nazionale.
- Un solo numero di contesto da un altro indicatore, se serve: nessuno è necessario.

## 6. Cose da NON scrivere
- Non scrivere che la scheda dice quanta energia (non solo elettrica) è rinnovabile, né «autosufficienza energetica». Solo elettricità, solo fonti rinnovabili, rapporto con il consumo interno lordo. Gas, carburanti e riscaldamento non ci sono.
- Non scrivere «il 327,8% dell'energia della Valle d'Aosta è rinnovabile»: una quota oltre 100 non è una percentuale di un tutto. Dire «produce più di tre volte i suoi consumi elettrici».
- Nessuna causa per i valori alti o i salti (esportazioni, siccità, incentivi, politiche regionali, clima, orografia) senza fonte aperta che la dica. Le fonti 2 e 3 descrivono, non spiegano.
- Non fare la divisione fra tavole 12.13 e 12.14 per «ricalcolare» l'indicatore: il denominatore è un altro (vedi fonte 4).
- Non chiamare «media nazionale» la media semplice delle regioni (66,63): il valore nazionale Istat è 41,7. Con la media dei tre territori oltre il 100 tolta sarebbe 40,85: nemmeno questa è nazionale.
- Non dire che una regione con quota alta è «più virtuosa» o con quota bassa «in ritardo»: la quota dipende anche da quanto consuma e da quali fiumi o venti ha. Un colore dei dati non porta un giudizio.
- Non scrivere «il Sud è davanti» senza il controllo sul prodotto assoluto (punto 4).
- Non attribuire al Trentino-Alto Adige un valore «delle sue province» (somma o media): Bolzano e Trento sono dati Istat separati.
- Non dire che la serie «cresce ogni anno»: nel 2022 scende in Italia (30,7) e in 15 regioni su 20.
- Stile: niente `—`, `–`, `;`, `…`. Niente «dal Nord al Sud» come falso intervallo. Niente domanda retorica in chiusura. Un numero o l'immagine, non tutti e due.

## 7. Struttura proposta (lead + 4 sezioni, ruolo `libera`, 600-800 parole)
- **Lead** (60-80 parole). OBBLIGO (Gate A v3): entro le prime due frasi dice che questa scheda NON misura quanta energia rinnovabile c'è in Italia né quanta parte dell'energia che usiamo è rinnovabile, ma quanta elettricità le fonti rinnovabili producono in una regione rispetto all'elettricità che quella regione consuma. Poi il significato: la Valle d'Aosta ne produce più di tre volte i consumi, la Liguria circa un ottavo. Le cifre (327,8% e 12,4%, anno 2024) dopo.
- **Sez. 1 «Un rapporto, non una quantità»** (150-180 parole). Definizione Istat, fonte Terna, denominatore consumo interno lordo, perché si supera il 100 (con la frase Istat testuale). Quota nazionale 41,7 e perché non è 41,2. Fonti 1 e 2.
- **Sez. 2 «Dove la quota supera il 100%»** (150-180 parole). Valle d'Aosta, Trentino-Alto Adige (Bolzano e Trento), Basilicata. Di che cosa è fatta: l'acqua in valle (98,6%), il vento in Basilicata (74,7%). Un solo contrasto vivido: Valle d'Aosta contro Liguria. Fonte 3, anno 2023 detto.
- **Sez. 3 «Il Mezzogiorno ha passato il Nord»** (160-190 parole). 2004 contro 2024 per ripartizioni, il 2012 come anno del sorpasso, Puglia da 3,9 a 68,1. Subito dopo, in una frase sua, il caveat in assoluto Nord 57.007 contro Mezzogiorno 43.082 milioni di kWh nel 2023. Digressione sola: la serie nazionale 15,5 nel 2004, 41,7 nel 2024.
- **Sez. 4 «Quello che il numero non dice»** (120-150 parole). Anni a oscillazione alta (Valle d'Aosta e Trentino-Alto Adige) e il 2022, senza cause. Solo elettricità. Una regione può stare sopra 100 e consumare energia di altro tipo. Provincia disponibile ma non confrontabile 1 a 1 (non studiata qui). Chiude con il passo successivo: la vista `/province` della scheda e gli altri indicatori del tema Ambiente ed energia.
- Marcatori di figura: nessuno obbligatorio, grafici dinamici esistenti (`docs/INDICATOR_PAGES.md`). Ogni sezione con `<!-- claims: [...] -->`.

## 8. Tre titoli SEO possibili (`seo_title` ≤ 60 caratteri)
1. «Energia rinnovabile per regione: quanta elettricità copre» (il più vicino alla ricerca).
2. «Elettricità rinnovabile: Valle d'Aosta 328%, Liguria 12%» (cifre in titolo, promette il contrasto).
3. «Elettricità da fonti rinnovabili: le regioni a confronto» (nome dell'indicatore, 56).
Raccomandazione: il 1 per il `seo_title`, con h1 narrativo diverso, per esempio «La Valle d'Aosta produce più di tre volte l'elettricità rinnovabile che consuma, la Liguria circa un ottavo» (da verificare: 327,8/100 = 3,3 e 1/0,124 = 8,1).

## 9. Gruppo di query a cui risponde
Solo la parola di testa «energia rinnovabile» ha un volume (5.400 al mese, Semrush db it, 08/10/2026, dato del titolare). Le altre sono plausibili, non misurate.
- «energia rinnovabile» (5.400 al mese): **la corrispondenza è parziale**. La query è generica (che cos'è, quanta ce n'è, in quali forme). La scheda copre solo l'elettricità rinnovabile e solo il rapporto con i consumi regionali. Il lead deve dirlo, altrimenti chi cerca «che cos'è l'energia rinnovabile» o la quota sui consumi totali non la trova.
- «energia rinnovabile per regione», «regioni con più energia rinnovabile», «percentuale di energia elettrica da fonti rinnovabili Italia», «produzione di energia rinnovabile per regione». Plausibili, la scheda risponde.
- «quanta energia rinnovabile produce l'Italia in kWh o GW»: **non risponde**. Il nostro dato è una quota, non una produzione assoluta (la tavola Terna 2023 dà 116.578,6 milioni di kWh, ma è un'altra grandezza).
- «energia rinnovabile sul totale dell'energia consumata»: **non risponde**, e nessuna fonte aperta da me lo dà.
