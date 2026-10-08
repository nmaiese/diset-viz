level: regione

# Brief scheda ricca: Infortuni mortali e inabilità permanente (`bes:03LAV007`)

Tipo di pezzo: scheda indicatore (non blog). Livello: regione, 20 regioni. Ultimo anno: 2022 (serie 2018-2022, tutti gli anni con 20 regioni). Fonte del dato: Istat, Bes dei territori, edizione 2025 (dicembre 2025), numeratore INAIL. Dati: `numeri.md` (ricalcolati qui sotto). Fonti: `fonti.md`. Lunghezza: 600-800 parole, lead compreso. Nessuna persona citata, nessun dato personale. Argomento di cronaca e di morti: tono sobrio, nessun aggettivo emotivo.

## Requisito del front matter
`level: regione`, `key: "bes:03LAV007"`, `vintage: 2022`, `fonti` con le fonti 1, 2 e 3 di `fonti.md` (la 4 e la 5 solo se la sezione dei limiti le usa davvero), `h1`, `seo_title` ≤ 60 caratteri. Il 2022 è **provvisorio** per Istat (Dominio 03: «2022(*)»): va detto una volta, nei limiti.

## Numeri chiave ricalcolati dal CSV (`Assoluti_BES_Regione.csv`, 20 regioni, per 10.000 occupati)
- 2022: massimo Umbria 17,8, minimo Piemonte 8,0, media semplice delle regioni 12,42 (mediana 12,35). Valore nazionale Istat 2022: **11,0** (fonte 1). La media semplice non è il valore nazionale.
- Distanza massimo-minimo: 16,2 punti nel 2018, 9,8 nel 2022.
- 2018-2022: scendono 15 regioni su 20, salgono 3, 2 invariate. 2019-2022: scendono 16, salgono 4.
- Basilicata 24,1 (2018) e 16,8 (2022); Umbria 18,2 e 17,8; Piemonte 8,2 e 8,0; Lombardia 7,9 e 8,1; Lazio 8,2 e 8,2.

## 1. Domanda del lettore
Chi cerca «morti sul lavoro» (2.400 al mese, Semrush db it, 08/10/2026) vuole sapere quante persone muoiono lavorando e dove. «Infortuni sul lavoro» (1.900) vuole una mappa del rischio. La scheda risponde in modo **parziale**: dà una mappa regionale del tasso di infortuni gravi (mortali e con inabilità permanente), non il numero delle morti. Va detto subito.

## 2. Tesi in una frase (un messaggio da dire a un amico)
Nel 2022 gli infortuni sul lavoro mortali e con inabilità permanente vanno da 8,0 ogni 10.000 occupati in Piemonte a 17,8 in Umbria, più del doppio, e in cinque anni la distanza fra le regioni si è ridotta soprattutto perché sono scese quelle in cima, non perché sia salito il fondo. È un confronto descrittivo fra tassi regionali, non una spiegazione del perché.

## 3. Esempi territoriali (dai dati)
1. **Umbria e Piemonte** (2022): 17,8 contro 8,0. In Umbria circa uno ogni 560 occupati, in Piemonte uno ogni 1.250 (1/17,8 × 10.000 = 562; 1/8,0 × 10.000 = 1.250). Umbria è prima solo nel 2022: nel 2018 era a 18,2 e il massimo era Basilicata.
2. **Basilicata**: 24,1 nel 2018, 16,8 nel 2022, il calo più grande (-7,3 punti). Il numero è piccolo: INAIL conta 7 infortuni mortali accertati nel 2022 in regione, 13 nel 2024 (fonte 4). Una regione piccola dà una serie nervosa.
3. **Calabria dentro la regione** (fonte Istat 2, 2022): 13,5 per la regione, Catanzaro 8,0, Reggio di Calabria 17,3. Il valore regionale nasconde una distanza più larga di quella fra molte coppie di regioni. Il rinvio è alla vista `/province` della scheda.
Facoltativo: **Lombardia, Lazio e Piemonte** fermi fra 7,7 e 8,3 in tutti i cinque anni.

## 4. Risultato non ovvio e controllo dei contrari
**Risultato**: la regione col tasso più alto cambia (Basilicata dal 2018 al 2021, Umbria nel 2022) e la distanza fra estremi si accorcia (16,2 a 9,8), ma il fondo non si muove: Lombardia, Lazio, Piemonte stanno intorno a 8 in ogni anno. Il cambiamento viene dall'alto.

**Controllo dei contrari** (fatto sui dati):
- «Allora Umbria è la regione più pericolosa.» No, in senso stretto: nel 2022 è prima per un punto (17,8 contro 16,8 e 16,7), con Basilicata e Abruzzo subito dietro, ed è piatta dal 2018 (18,2). Il primo posto è un effetto del calo di Basilicata. Dire «la più alta nel 2022», mai «la più pericolosa».
- «Il calo è un miglioramento certo.» Non dimostrabile: il 2022 è provvisorio per Istat, la serie ha cinque anni, il 2020 è un anno anomalo (media semplice delle regioni 12,2 contro 13,5 del 2019, massimo 17,1 contro 23,3). Nessuna fonte letta spiega il 2020 e non si deve attribuirlo a nulla. Si può dire «scende in 15 regioni su 20 fra 2018 e 2022».
- «L'Italia sta a 11 e la media è 12,4, quindi il dato è sbagliato.» No: 11,0 è il valore nazionale Istat (pesato sugli occupati), 12,4 la media semplice delle 20 regioni. Le regioni grandi e basse (Lombardia, Lazio) pesano molto sul valore nazionale. Mai chiamare «media nazionale» il 12,4.
- «I conteggi INAIL confermano il tasso.» Non si può dire. INAIL pubblica conteggi per accadimento e stato amministrativo (fonti 3 e 4), il Bes un tasso con un numeratore il cui perimetro non è documentato (vedi `fonti.md`, «Non trovato»).

## 5. Dati ammessi
- Valori regionali 2018-2022 del CSV (`bes:03LAV007`): ordine, massimo, minimo, variazioni, conteggi di regioni che scendono.
- Italia 2019 e 2022 (11,7 e 11,0, provvisorio), Mezzogiorno 14,3 e 13,0: solo da Istat (fonte 1).
- Calabria 13,5, Catanzaro 8,0, Reggio di Calabria 17,3 (2022): da Istat (fonte 2); i valori provinciali coincidono con il CSV.
- INAIL: **un numero ciascuno, con l'unità e l'anno**, solo nei limiti. Esempi ammessi: Italia 572 infortuni accertati positivi con esito mortale nel 2024, 716 nel 2022 (fonte 3); 1.189 denunce di infortunio con esito mortale di lavoratori nel 2025 (fonte 5). Mai sommati, mai divisi per occupati, mai messi a confronto con il tasso.
- Province: ammessi Catanzaro, Reggio di Calabria e un rinvio a `/province`. Esiste già un articolo (`content/posts/2026-09-23-infortuni-lavoro-province.md`, «Infortuni gravi sul lavoro: i grandi settori non bastano a spiegare la mappa»): la scheda lo cita come approfondimento con un link, non ne riprende le tesi.

## 6. Cose da NON scrivere
- **Non scrivere «morti sul lavoro» come titolo del dato.** L'indicatore conta infortuni mortali **e** con inabilità permanente, in un tasso. Non è il numero dei morti, non è il numero di tutti gli infortuni (restano fuori i guariti e quelli con meno di una certa gravità, che il glossario non specifica), non include le malattie professionali.
- Non scrivere «si muore di più in Umbria»: non si sa quanti dei casi sono mortali. Il glossario non separa i due esiti.
- Nessuna causa del divario (settore, edilizia, agricoltura, dimensione d'impresa, lavoro nero, sotto-denuncia, controlli, sicurezza). Nessuna fonte letta le attribuisce a questi valori. In particolare **non** riprendere la frase della scheda attuale «Gli infortuni dipendono soprattutto da come è fatto il lavoro di un territorio»: è una spiegazione non sostenuta da una fonte aperta. Vale anche per «la sotto-denuncia in alcuni settori».
- Non scrivere «ogni infortunio grave resta un fallimento», «il lavoro uccide», «strage», né altro tono di commento.
- Nessuna correlazione con altri nostri indicatori (occupazione, reddito, PIL) come tesi.
- Non scrivere che 17,8 significa «17,8 persone ogni 10.000 muoiono». Tradurre in forma di rapporto (circa uno ogni 560 occupati) solo con «infortunio grave» e «occupati» in frase.
- Non dire che il dato è del 2023 o del 2024: l'ultimo anno del Bes è il 2022. Se si cita INAIL 2024 o 2025, anno e unità (accertati positivi, denunce) in frase.
- Non confrontare denunce (1.189 di lavoratori nel 2025) con accertati positivi (572 nel 2024): sono stati amministrativi diversi.
- Non scrivere «il Sud è più a rischio»: nel 2022 Umbria, Marche e Toscana (Centro) sono nei primi cinque, Lazio è quasi in fondo. La ripartizione non è la chiave.
- Non chiamare «media nazionale» il 12,4. Il valore nazionale Istat è 11,0.
- Stile: niente `—`, `–`, `;`, `…`. Niente domanda retorica in chiusura.

## 7. Struttura proposta (lead + 4 sezioni, ruolo `libera`, 600-800 parole)
- **Lead** (60-80 parole). OBBLIGO (Gate A v3): entro le prime due frasi dire che questa scheda **non conta le morti sul lavoro** ma il tasso di infortuni mortali **e** con inabilità permanente ogni 10.000 occupati, e che non comprende tutti gli infortuni. Poi il contrasto: nel 2022 da 8,0 in Piemonte a 17,8 in Umbria (più del doppio), anno e unità. Il valore nazionale 11,0 e «provvisorio» nei limiti, non nel lead.
- **Sez. 1 «Che cosa conta quel 17,8»** (140-170 parole). Definizione Istat (fonte 1), per 10.000 occupati, al netto delle forze armate, numeratore INAIL. Che cos'è un tasso e non un conteggio. Una frase: non separa morti e inabilità permanente. Rapporto «uno ogni 560 / 1.250 occupati».
- **Sez. 2 «Dove il tasso è più alto»** (160-190 parole). Umbria, Basilicata, Abruzzo, Marche, Toscana, 17,8 a 14,4: tre del Centro (Umbria, Marche, Toscana) e due del Mezzogiorno (Basilicata, Abruzzo). Lazio, Lombardia e Piemonte in fondo. Un solo contrasto vivido (Umbria e Piemonte). Il «più del doppio».
- **Sez. 3 «Cinque anni, il calo viene dall'alto»** (150-180 parole). Basilicata 24,1 → 16,8. Umbria piatta. Lombardia, Lazio, Piemonte ferme. Distanza da 16,2 a 9,8. 15 regioni su 20 scendono. Italia 11,7 → 11,0 dal 2019 (Istat). Il 2020 si cita come anno con valori più bassi, senza cause. Una digressione sola.
- **Sez. 4 «Quello che il numero non dice»** (140-170 parole). Il 2022 è provvisorio. Regioni piccole, numeri piccoli (Basilicata 7 mortali accertati nel 2022, INAIL fonte 4). Dentro la regione: Catanzaro 8,0, Reggio di Calabria 17,3 (Istat fonte 2). Differenza fra tasso Bes e conteggi INAIL (572 accertati positivi mortali nel 2024, 1.189 denunce mortali di lavoratori nel 2025): misure diverse, anni diversi, non confrontabili. Non include le malattie professionali. Chiude con il passo successivo: `/province` della scheda e l'articolo del 23/09/2026.
- Marcatori di figura: nessuno obbligatorio, grafici dinamici esistenti. Ogni sezione con `<!-- claims: [...] -->`.

## 8. Tre titoli SEO possibili (`seo_title` ≤ 60 caratteri)
1. «Infortuni gravi sul lavoro: dove pesano di più, per regione» (59). Parola di testa vicina a «infortuni sul lavoro», onesta su «gravi».
2. «Infortuni sul lavoro gravi: Umbria 17,8, Piemonte 8,0» (53). Cifre in titolo, promette il contrasto.
3. «Infortuni mortali e permanenti sul lavoro per regione» (52). Il più fedele all'indicatore, lontano da «morti sul lavoro».
Raccomandazione: il 1 per il `seo_title`, un h1 narrativo diverso, per esempio «Nel 2022 un infortunio grave ogni 560 occupati in Umbria, uno ogni 1.250 in Piemonte» (cifre già verificate sopra: 10.000/17,8 = 562, 10.000/8,0 = 1.250). Evitare «morti» in titolo: la parola promette il numero dei morti.

## 9. Gruppo di query a cui risponde
Solo plausibili, **senza volumi inventati** (solo le due parole di testa del titolare, Semrush db it, 08/10/2026):
- «morti sul lavoro» (2.400 al mese): **corrispondenza parziale**. La scheda non dà il numero dei morti, né l'anno corrente. Il lead lo dichiara. Chi cerca il conteggio troverebbe INAIL (1.189 denunce di lavoratori nel 2025, nei limiti).
- «infortuni sul lavoro» (1.900 al mese): **corrispondenza parziale**. Risponde per la parte grave (mortale o con inabilità permanente) e per regione, non per tutti gli infortuni.
- Plausibili, non misurate: «infortuni sul lavoro per regione», «infortuni gravi sul lavoro regioni», «dove ci sono più infortuni sul lavoro», «tasso infortuni sul lavoro per regione», «infortuni sul lavoro Umbria».
- **Non risponde**: «quanti morti sul lavoro nel 2025/2024» (qui l'ultimo anno è il 2022), «morti sul lavoro per settore», «morti sul lavoro per mese». Nessun dato.
