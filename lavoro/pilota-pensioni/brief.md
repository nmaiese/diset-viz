level: provincia

# Brief scheda pilota: Pensionati con reddito pensionistico di basso importo (`bes:04BEC006P`)

Tipo di pezzo: scheda indicatore (non blog). Livello: provincia, 107 province. Ultimo anno: 2023 (Istat, Bes dei territori 2025, dicembre 2025). Dati: `numeri.md`. Fonti: `fonti.md`. Lunghezza: 600-800 parole, lead compreso. Nessuna persona citata, nessun dato personale.

## Requisito del front matter
`level: provincia`. Inoltre `key: "bes:04BEC006P"`, `vintage: 2023`, `fonti` con le fonti 1, 2 e 4 di `fonti.md` (la 3, INPS 1.1.2026, solo se la sezione dei limiti la usa davvero), `h1`, `seo_title` ≤ 60 caratteri.

## 1. Domanda del lettore
Quanti pensionati prendono una pensione bassa e dove? Chi cerca «pensioni minime» o «pensione bassa» vuole sapere dove si sta peggio e se sta migliorando. La scheda risponde con una quota, non con un numero di persone.

## 2. Tesi in una frase (un messaggio da dire a un amico)
Nel 2023 la quota di pensionati con un reddito pensionistico sotto i 500 euro lordi al mese va dal 16,9% di Crotone al 4,1% di Bolzano, e in nove anni è scesa quasi ovunque senza che la distanza fra i due estremi si chiudesse. È una fotografia di quote per territorio, non l'effetto del luogo in cui si vive.

## 3. Esempi territoriali (dai dati, `numeri.md`)
1. **Crotone e Biella** (2023): 16,9% contro 4,9%. Crotone è prima per quota, ultima per importo medio (16.309 euro l'anno). Biella è penultima per quota, seconda dal fondo dopo Bolzano.
2. **Napoli e Milano**: Napoli 15,6% (terza), Milano 6,0% (novantesima). Nel 2015 erano 18,9 e 7,4: entrambe scendono, di 3,3 e di 1,4 punti, la distanza resta.
3. (Facoltativo, solo se serve spazio) **Isernia contro Verbano-Cusio-Ossola**: la meno colpita del Mezzogiorno, 9,2%, sta sopra la più alta del Nord, 8,9%. Le prime 20 province per quota sono tutte del Mezzogiorno.

## 4. Risultato non ovvio e controllo dei contrari
**Risultato**: la quota scende in tutte le 106 province con dati nel 2015 e nel 2023 (nessuna sale), eppure la distanza fra la più alta e la più bassa resta intorno ai 13 punti (13,2 nel 2015, 12,8 nel 2023).

**Controllo dei contrari** (fatto sui dati):
- «Allora il Sud ha recuperato.» Sì in punti (Mezzogiorno da 14,8 a 12,8 fra 2019 e 2023, Istat), ma anche l'Italia scende da 10,4 a 8,9: la distanza dal valore nazionale non cambia molto. Non scrivere «recupera» senza il confronto.
- «Il calo è un effetto statistico.» Possibile: la soglia di 500 euro è nominale e fissa, le pensioni vengono rivalutate. **Nessuna fonte aperta lo conferma** (vedi `fonti.md`, «Non trovato»). Si dice come limite della misura («500 euro lordi, in euro correnti»), mai come spiegazione del calo.
- «Il minimo e il massimo sono rumore.» Il massimo è Crotone in tutti i nove anni. Il minimo cambia nome (Ferrara, Biella, Bolzano) perché i decimali sono vicini: per questo il minimo non fa parte della tesi se non per il 2023.
- **Bolzano 2023**: 6,9 nel 2022 e 4,1 nel 2023, un salto di 2,8 punti in un anno (media nazionale delle province: -0,36). Non so se sia una discontinuità della serie. Il pezzo può dire che è il valore più basso del 2023, non che «Bolzano è migliorata di 4,5 punti» come fatto strutturale.

## 5. Dati ammessi
- Valori provinciali 2015-2023 del CSV del sito (`bes:04BEC006P`), per ripartizione e per ordinale.
- Italia e Mezzogiorno 2019 e 2023, Calabria e Trentino-Alto Adige 2023: solo da Istat (fonti 1 e 2).
- `bes:04BEC005P` (importo medio annuo pro-capite dei redditi pensionistici): ammesso come **un numero** per Crotone (16.309 euro) e per Milano (26.348,5), mai come tesi né come correlazione.
- INPS 1.1.2026 (fonte 3): solo per la frase di limite, citando che la pensione bassa non è il reddito della persona. Anno e unità (pensioni, soglia 750) vanno detti.

## 6. Cose da NON scrivere
- Nessuna causa del divario (lavoro irregolare, carriere discontinue, genere, struttura produttiva) senza fonte aperta. Nelle fonti raccolte non c'è.
- Nessuna correlazione con altri nostri indicatori come tesi (reddito disponibile, occupazione, PIL pro capite): ammessi solo come numeri di contesto, e non servono.
- Nessun conteggio di persone: «un pensionato su sei a Crotone» è una traduzione della quota, ammessa se l'unità resta chiara («una quota»). Mai «16,9 per cento dei calabresi».
- Non scrivere che 500 euro lordi sono «la pensione minima» né «la soglia di povertà»: la pensione minima è un'altra cosa (integrazione al minimo, INPS). Non confondere.
- Non scrivere che il 16,9% vive con meno di 500 euro: il reddito pensionistico non è il reddito familiare (altri redditi, cumulo di pensioni, reversibilità, coniuge).
- Non dire che l'integrazione al minimo, le pensioni sociali o l'invalidità civile sono dentro o fuori il «reddito pensionistico» dell'indicatore: il glossario non lo chiarisce.
- Non chiamare «media nazionale» la media semplice delle province (8,856). Il valore nazionale Istat è 8,9 e va citato come tale.
- Nessuna causa per il salto dell'importo medio 2022 -> 2023 (+7,2% la media semplice).
- Stile: niente `—`, `–`, `;`, `…`. Niente «dal Nord al Sud» come falso intervallo. Niente domanda retorica in chiusura.

## 7. Struttura proposta (lead + 4 sezioni, ruolo `libera`, 600-800 parole)
Diversa dallo schema fisso `definizione, quadro, dinamica, limiti`. Una sezione per movimento della storia.

- **Lead** (60-80 parole). OBBLIGO (Gate A v3, correzione 1): il lead dice entro le prime due frasi che questa scheda NON misura la pensione minima INPS (il trattamento minimo, integrazione al minimo) ma la quota di pensionati con reddito pensionistico lordo sotto 500 euro al mese; chi cerca «pensioni minime» deve capirlo subito. Apre sul significato: a Crotone circa un pensionato su sei ha un reddito pensionistico sotto i 500 euro lordi al mese, a Bolzano uno su ventiquattro. Il 16,9% e il 4,1% arrivano dopo, con l'anno, 2023. (Per scala umana usa una sola delle due forme: l'immagine o la cifra.)
- **Sez. 1 «Che cosa conta davvero quel 16,9%»** (150-180 parole). Definizione Istat, soglia, tasso e non persone. Pensione non è reddito. Una frase sua per il caveat. Fonti 1 e 2.
- **Sez. 2 «Dove una pensione bassa è la regola»** (170-200 parole). Le prime venti del Mezzogiorno. Isernia sopra Verbano-Cusio-Ossola. Crotone contro Biella. Un solo contrasto vivido.
- **Sez. 3 «Nove anni, un calo ovunque»** (150-180 parole). Scende in tutte le province, distanza intorno ai 13 punti, Napoli e Milano 2015 e 2023, Italia 10,4 -> 8,9. Una digressione sola: il Mezzogiorno 14,8 -> 12,8.
- **Sez. 4 «Quello che il numero non dice»** (120-150 parole). Dire anche che la fonte Istat non chiarisce se la provincia indichi la residenza del pensionato o il luogo di erogazione della pensione (limite territoriale non documentato, Gate A v3, correzione 3). Pensioni multiple, reversibilità, integrazione al minimo. Il fatto di Bolzano come limite del dato. L'INPS (1.1.2026, soglia 750, pensioni e non pensionati). Chiude con il passo successivo: l'importo medio (`bes-04BEC005P`) e la `/province` della scheda.
- Marcatori di figura: nessuno obbligatorio, usa i grafici dinamici esistenti (`docs/INDICATOR_PAGES.md`). Ogni sezione con `<!-- claims: [...] -->`.

## 8. Tre titoli SEO possibili (`seo_title` ≤ 60 caratteri)
1. «Pensioni basse: dove pesano di più, provincia per provincia» (59). Parola di testa «pensioni basse», più vicina alla ricerca.
2. «Pensione sotto i 500 euro: Crotone 16,9%, Bolzano 4,1%» (54). Cifre in titolo, promette il contrasto.
3. «Pensionati sotto i 500 euro al mese: dove sono di più» (53). Risponde alla domanda «dove».
Raccomandazione: il 3 per il `seo_title` e un h1 narrativo diverso, per esempio «A Crotone quasi un pensionato su sei prende meno di 500 euro, a Bolzano uno su ventiquattro» (da verificare: 1/16,9% = 5,9; 1/4,1% = 24,4).

## 9. Gruppo di query a cui risponde
Query plausibili da Istat e INPS, **senza volumi inventati** (solo la parola di testa «pensioni minime», 3.600 al mese, Semrush db it, dato del titolare):
- «pensioni minime» (3.600 al mese): **la corrispondenza è parziale**. La scheda non parla della pensione minima INPS (integrazione al minimo) ma di una quota sotto 500 euro lordi. Il lead deve dirlo subito, altrimenti il lettore ci cerca dentro la cifra del trattamento minimo e non la trova.
- «pensione bassa», «pensioni basse per regione/provincia», «quanti pensionati prendono meno di 500 euro», «pensionati sotto i 500 euro al mese». Plausibili, non misurate.
- «quanti pensionati prendono meno di 1000 euro»: **non risponde**. Il nostro dato ha soglia 500. L'INPS dà la soglia 750 (pensioni, non pensionati). Una soglia di 1.000 euro non c'è in nessuna fonte aperta da me.
