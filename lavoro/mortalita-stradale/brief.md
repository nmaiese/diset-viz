level: regione

# Brief scheda: Mortalità per incidenti stradali (15-34 anni) (`bes:01SAL005`)

Tipo di pezzo: scheda indicatore (non blog). Livello: regione, 20 regioni. Ultimo anno: 2024 (Istat, Bes aggiornamento intermedio 2026, file del 25/05/2026). Dati: ricalcolati dal CSV `app/static/data/Assoluti_BES_Regione.csv` l'8/10/2026, riportati qui sotto. Fonti: `fonti.md`. Lunghezza: 600-800 parole di prosa, lead compreso. Nessuna persona citata, nessun dato personale. Esiste già una scheda breve (`content/indicators/bes__01SAL005.md`): va riscritta, vedi sezione 6.

## Requisito del front matter
`level: "regione"`, `key: "bes:01SAL005"`, `vintage: 2024`, `fonti` con le fonti 1, 2 e 3 di `fonti.md` (la 5 solo se la sezione 4 usa il fatto sardo dei 113 morti, la 4 solo come contesto 2025), `h1`, `seo_title` ≤ 60 caratteri.

## 1. Domanda del lettore
Dove muoiono più giovani sulla strada, e va meglio di vent'anni fa? Chi cerca «incidenti stradali» vuole di solito la cronaca di oggi o il totale dei morti in Italia. Questa scheda risponde a una domanda più stretta: il rischio di morire in un incidente per chi ha tra 15 e 34 anni, regione per regione.

## 2. Tesi in una frase
Nel 2024 il tasso standardizzato di mortalità stradale tra i 15 e i 34 anni va da 1,3 ogni 10.000 giovani residenti in Sardegna a 0,4 in Liguria, Marche, Molise e Piemonte, ed è sceso in tutte e 20 le regioni dal 2004. Sono tassi bassi su pochi decessi, a un solo decimale: l'ordine delle regioni cambia da un anno all'altro, tranne la Sardegna, che resta in testa anche sulla media di tre anni.

## 3. Esempi territoriali (dai dati)
1. **Sardegna e Piemonte, Liguria, Marche, Molise** (2024): 1,3 contro 0,4. La Sardegna è sola in testa nel 2024 (la seconda, Calabria e Puglia, ha 0,9) ma ci sta anche sulla media semplice di tre anni: 0,97 nel 2022-24 contro 0,90 della Basilicata (media di tre tassi annuali, non un tasso triennale). Nel 2023 era a 0,8, a pari merito con altre cinque regioni.
2. **Calabria** e **Molise**: Calabria 0,5 nel 2023 e 0,9 nel 2024. Molise 1,8 nel 2017, 0,3 nel 2018, 0,2 nel 2023, 0,4 nel 2024. Servono per far vedere quanto un decimale si muove.
3. (Facoltativo) **Valle d'Aosta**: 0,4 nel 2016, 2,4 nel 2017, 0,4 nel 2018, nessun valore nei dati 2019-2021. È la regione meno popolosa: lo dico come cautela sui piccoli numeri, senza una cifra di popolazione.

## 4. Risultato non ovvio e controllo dei contrari
**Risultato**: il calo è ovunque (20 regioni su 20 scendono dal 2004 al 2024), ma non allo stesso passo, e la geografia si è rovesciata. Nel 2004-06 il Mezzogiorno aveva il tasso medio più basso (1,54 contro 1,89 del Nord e 1,77 del Centro, medie semplici delle regioni di ciascuna ripartizione). Nel 2022-24 è il più alto (0,70 contro 0,60 e 0,62). Le regioni che scendono meno sono Calabria e Campania (da 1,2 e 1,1 a 0,9 e 0,8, cioè -0,3), Basilicata e Sardegna (-0,4). Quelle che scendono di più sono l'Emilia-Romagna (da 2,7 a 0,6), il Piemonte, la Toscana e il Trentino-Alto Adige (-1,6).

**Controllo dei contrari**:
- «Allora il Sud è più pericoloso.» Solo di poco: 0,70 contro 0,60 sul triennio sono un decimo, dello stesso ordine dell'arrotondamento del dato. Nel 2024 il quadro è meno pulito: Umbria e Valle d'Aosta stanno a 0,8, come Abruzzo, Basilicata e Campania. Va detto «il divario si è invertito di poco», mai «il Sud è peggio».
- «Il picco sardo 2024 è un fatto sardo.» Non lo sappiamo. Nel 2024 le vittime di tutte le età in Sardegna sono 113 contro 110 del 2023 (Istat, fonte 5), mentre il nostro tasso 15-34 passa da 0,8 a 1,3. Per l'Italia i morti di 20-24 e 25-29 anni crescono nel 2024 (+13,0% e +10,9%, Prospetto 3, fonte 3), e nel nostro CSV la media semplice sale da 0,59 a 0,685 e 9 regioni su 20 salgono (4 scendono, 7 invariate). Il 1,3 si legge insieme al 2023 e al 2022, non da solo.
- «Il calo è finito.» Il 2025 non è nel nostro indicatore. L'Istat dice che nel 2025 i morti nazionali di 20-24 e 25-29 anni scendono (-9,1% e -19,2%, fonte 4), ma è un conteggio nazionale e non una previsione per le regioni. Non scrivere né «ripresa» né «risalita».
- «Il minimo è sempre la stessa regione.» No: Liguria, Marche, Molise e Piemonte sono a pari merito nel 2024, e il minimo cambia nome quasi ogni anno. Non nominare «la più sicura».

## 5. Dati ammessi
- Serie regionali 2004-2024 del CSV (`bes:01SAL005`), valori a un decimale, medie semplici di regioni sempre dichiarate come tali.
- Italia 2023 = 0,6 e Mezzogiorno 2023 = 0,6 (Istat, Bes dei territori 2025, fonte 2), con l'anno. Il 2024 nazionale **non** c'è: non scriverlo.
- Province sarde 2023 (fonte 2): Cagliari 1,3 e Oristano 0,0. Ammessi solo per mostrare la scala dei decimali dentro una stessa regione.
- Nazionale (fonti 3, 4): 3.030 morti nel 2024 e 2.868 nel 2025 (tutte le età), 773 morti tra 15 e 34 anni nel 2024 (somma delle classi 15-17, 18-19, 20-24, 25-29, 30-34 del Prospetto 3). Dire sempre «morti entro 30 giorni» e che sono conteggi, non tassi.
- Sardegna 113 morti nel 2024 contro 110 nel 2023, tutte le età (fonte 5).

## 6. Cose da NON scrivere
- **Nessuna causa di geografia o di calo senza fonte aperta.** La scheda attuale scrive che il calo viene da «veicoli più sicuri, controlli, campagne e norme» e che la Sardegna ha «lunghe percorrenze e trasporto pubblico limitato»: nelle fonti raccolte non c'è, va tolto. Niente strade, alcol, velocità, distanze, turismo, auto, trasporto pubblico.
- **Nessuna frase sul «raro esempio di politica pubblica che sposta i numeri» né su «vite giovani spezzate»**: la prima è una causa, la seconda è enfasi che il dato non regge.
- Non scrivere che il tasso è «sul totale dei residenti» né che «l'1,3 è la quota di giovani che muoiono». È un tasso su 10.000 residenti della classe 15-34, standardizzato. Non tradurlo in «un giovane su 7.700» e non dire «morti» senza il periodo e l'unità.
- Non chiamare «media nazionale» la media semplice delle regioni (0,685 nel 2024). Il valore Istat Italia è 0,6 solo per il 2023.
- Non attribuire i decessi alla regione di residenza o a quella dell'incidente. Il glossario non lo dice (`fonti.md`, «Non trovato»).
- Non confrontare 1,3 per 10.000 con i tassi per milione (84,7 nei 20-24, fonte 3) o con il 15,8 per 100.000 della classe 15-29 sarda (fonte 5): classi, unità e standardizzazione diverse.
- Non usare il «+23,9%» del testo del report Istat 2024: il suo Prospetto 3 dà +13,0% e +10,9%.
- Non dire che «la Sardegna è la regione più pericolosa». È la prima nel 2024 e sulla media 2022-24, ma i numeri sono piccoli: dirlo come «tasso più alto» e con l'anno.
- Nessuna correlazione con altri nostri indicatori come tesi (strade, trasporto, reddito, mortalità evitabile).
- Nessuna persona, nessun caso di cronaca, nessuna statistica del 2025 sul tasso regionale.
- Stile: niente `—`, `–`, `;`, `…`. Niente domanda retorica in chiusura.

## 7. Struttura proposta (lead + 4 sezioni, ruolo `libera`, 600-800 parole)
- **Lead** (60-80 parole). OBBLIGO (Gate A v3, correzione 1): entro le prime due frasi dice che l'indicatore NON conta gli incidenti stradali né tutte le vittime, e che non riguarda i feriti: misura quanti giovani tra 15 e 34 anni muoiono in un incidente ogni 10.000 residenti della stessa età, per regione. Prima frase suggerita: «Questa scheda non conta gli incidenti stradali né tutte le vittime della strada: misura quanti giovani tra i 15 e i 34 anni muoiono in un incidente ogni 10.000 residenti di quell'età.» Seconda: «Nel 2024 il tasso è 1,3 in Sardegna e 0,4 in Liguria, Marche, Molise e Piemonte.» Poi il limite: pochi decessi, un solo decimale.
- **Sez. 1 «Che cosa misura quell'1,3»** (140-170 parole). Definizione Istat (fonte 1), classe 15-34, standardizzazione sulla popolazione europea 2013 spiegata in una frase, tasso e non conteggio. Che cosa non è: cronaca, totale dei morti (3.030 nel 2024, Istat), feriti, incidenti senza vittime. Fonte primaria: rilevazione Istat sugli incidenti con lesioni a persone.
- **Sez. 2 «Dove il tasso è più alto»** (150-180 parole). Sardegna 1,3 contro Calabria e Puglia 0,9. Sardegna anche sulla media 2022-24 (0,97 contro 0,90 della Basilicata, dichiarata media di tre tassi). Le quattro regioni a 0,4. Italia 0,6 (2023).
- **Sez. 3 «Vent'anni di calo, un ordine rovesciato»** (170-200 parole). 20 regioni su 20 scendono, Emilia-Romagna da 2,7 a 0,6. Il Mezzogiorno da più basso a più alto, sulle tre annate (1,54 contro 1,89, poi 0,70 contro 0,60). Una sola digressione: l'inversione è di un decimo.
- **Sez. 4 «Quanto pesa un decimale»** (130-160 parole). Calabria 0,5 e 0,9, Molise 1,8 e 0,3, Sardegna 0,8 e 1,3 con le vittime sarde di tutte le età 110 e 113. Cagliari 1,3 e Oristano 0,0 nel 2023. Nel 2024 la media semplice dei 20 tassi regionali sale e 9 regioni su 20 aumentano, poi una frase sui conteggi Istat dei 20-29 anni. Poi i limiti: non sappiamo quanti decessi ci sono dietro, né se contano la regione dell'incidente o di residenza. Valle d'Aosta senza valori 2019-2021. Chiude con ciò che il dato non dice: feriti, incidenti senza vittime, chi guida o chi è trasportato.
- Marcatori di figura: nessuno obbligatorio, usa i grafici dinamici esistenti (`docs/INDICATOR_PAGES.md`). Ogni sezione con `<!-- claims: [...] -->`.

## 8. Tre titoli SEO possibili (`seo_title` ≤ 60 caratteri)
1. «Mortalità stradale dei giovani (15-34 anni) per regione» (55). Parola «mortalità stradale», la più vicina alla ricerca.
2. «Morti in strada a 15-34 anni: da 1,3 in Sardegna a 0,4» (54). Cifre in titolo, promette il contrasto. Non nomina un minimo unico, perché ce ne sono quattro.
3. «Giovani e strada: dove il tasso di morte è più alto» (51). Risponde alla domanda «dove».
Raccomandazione: il 1 per il `seo_title` (la formula automatica di `seo_titles.page_title` aggiunge la coda del livello: da verificare che non sfori i 60 caratteri), e un h1 narrativo diverso, per esempio «Nel 2024 in Sardegna muoiono in un incidente 1,3 giovani ogni 10.000, in quattro regioni 0,4». Le quattro (Liguria, Marche, Molise, Piemonte) sono di tre ripartizioni diverse: non scrivere «Centro-Nord» né «Nord» come sintesi.

## 9. Gruppo di query a cui risponde
Query plausibili da Istat, **senza volumi inventati** (solo la parola di testa «incidenti stradali», 4.400 al mese, Semrush db it, dato del titolare, 08/10/2026):
- «incidenti stradali» (4.400 al mese): **la corrispondenza è parziale e debole**. La scheda non dà cronaca né il totale dei morti né la lista degli incidenti: dà un tasso di mortalità tra 15 e 34 anni per regione. Il lead lo dice entro due frasi, altrimenti il lettore cerca la cronaca di oggi e non la trova.
- «mortalità stradale giovani», «morti in incidenti stradali giovani per regione», «incidenti stradali 15-34 anni», «regione con più morti sulla strada tra i giovani»: plausibili, non misurate.
- «quanti morti in incidenti stradali in Italia»: **non risponde** (il nostro dato non è un totale). Il 3.030 del 2024 è un contesto Istat, da citare con la sua fonte.
- «incidenti stradali oggi», «ultime notizie incidenti», «incidenti stradali per provincia»: **non risponde**. Il nostro livello è la regione, e non c'è un livello provinciale per questo indicatore nella scheda.
