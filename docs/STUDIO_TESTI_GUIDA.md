# Studio dei testi di guida e spiegazione, giochi compresi

Redatto il 1 ottobre 2026. È uno **studio**: nessun testo del sito è stato modificato. Completa `docs/STUDIO_TESTI.md`, che riguarda i tag title e le meta description e non va ripetuto. Qui si parla dei testi che dicono che cos'è il sito, come si legge un dato o una classifica, che cosa vuol dire un termine, che cosa fare dopo, e dei testi dei cinque giochi di Sfida Italia (regole, errori, esiti, condivisione).

## 1. Come è stato fatto, e quanto fidarsi

Tre worker Orca (nessun Codex) più i dati di prima mano di chi coordina: corpus del testo visibile di 24 pagine di produzione del 1/10/2026, indice di leggibilità Gulpease per pagina, Search Console a 90 giorni, Semrush Italia.

| Fonte | Esito della verifica |
| --- | --- |
| **Audit interno** (claude sonnet, circa 22.000 parole, letto dal sorgente di template, `app/design`, `frontend/src/game`, `docs/GIOCO.md` e un campione di `content/`) | **È la base di questo studio.** Ho ricontrollato nel codice quattro affermazioni pesanti: la locuzione "media semplice" non compare in `v1/metodologia.html`; "DISET" sta nel testo pubblico a `metodologia.html:162`; non esiste un `errorhandler(500)`; l'esportazione e l'eliminazione dell'account in `auth.js` non mostrano nessun errore se falliscono. Tutte esatte. Dichiara di non aver eseguito l'app né provato i giochi in un browser |
| **Evidenza e SEO** (claude sonnet) | Buona sulle fonti ufficiali: ricontrollato Google, FAQ rich result spenti dal 7 maggio 2026. **Sbaglia in un punto**: dice che la ricerca senza risultati non mostra il messaggio, ma il messaggio c'è (`ricerca.html:61`), il corpus tagliava la testata. Le fonti accademiche (PNAS, ACM, SAGE) erano bloccate: segnate non verificate |
| **Competitor** (antigravity) | **Poco affidabile, usato solo in parte.** Verificate a mano: la frase di OWID ("a free, non-profit website. Our mission...") e la sostanza di Lab24 sul punteggio (1.000 punti al migliore, 0 al peggiore, verso deciso dalla redazione), ma la sua citazione di Lab24 non è letterale. Le percentuali ("8 siti su 10") non sono credibili, alcune citazioni non sono verificabili (Wordle, bloccato) o sono sospette (un quiz de Il Post). Il rapporto al momento della sintesi conteneva ancora lo script che lo scrive, non il testo. Non uso i suoi conteggi |

Conseguenza: sui competitor lo studio dice poco di verificato. Dove mancano evidenza e confronto lo dichiaro.

## 2. Che cosa è emerso

Il sito ha un buon istinto: dice i limiti, non chiama "media nazionale" la media delle regioni, ha un blocco "Come leggere il dato" su ogni scheda e un piccolo glossario a popover. **Il problema non è la voce, è dove sta la spiegazione**: ogni pagina spiega da sé con parole sue, e la pagina a cui tutte rimandano non spiega quasi niente di ciò che le si chiede.

### I problemi che spostano di più (da audit, ordinati)

1. **`/metodologia` è la meta di una ventina di link "Come si calcola" ma non definisce "media semplice", "n.d.", "copertura variabile", "posizione media", "percentile medio", "Cambiato di più".** I popover di `app/design/terms.py` puntano lì e quattro su cinque non ci trovano la propria definizione. La risposta migliore alla domanda "la media mostrata è la media italiana?" sta in `divari-regionali.html:216`, che nessuno cita. *(Verificato per "media semplice".)*
2. **"Punteggio" ha tre metodi con lo stesso nome**: z-score orientato (qualità della vita), media dei percentili (pagina tema), posizione media (pagina regione). Il popover dice "50 è la media semplice dei territori", vero per il primo e non per il secondo.
3. **Nel gioco Chi è maggiore? "va in classifica" è ambiguo.** Il testo promette che la partita a tempo "va in classifica", ma la sola classifica pubblica è quella delle serie a round: la sfida del giorno conta come record personale. Chi gioca a tempo cerca una classifica che non c'è. Si risolve cambiando una parola nei due punti in cui compare.
4. **Il lead di Indovina la Regione promette "più vicino o più lontano"**, ma il gioco dà solo "più alto o più basso" e "stessa ripartizione". "Ripartizione" non è mai definita.
5. **Indovina la Provincia dà distanze senza la parola "stima".** `docs/GIOCO.md` chiede che il testo lo dica ed è coperto a metà (la mappa lo dice, la provincia no).
6. **Mancano del tutto**: la pagina 500 (si vede quella inglese di Werkzeug, verificato), un messaggio quando "Esporta" o "Elimina account" falliscono (la persona conferma e non succede niente), una frase su che cosa dà un account al punto in cui si decide di accedere. *(500 e account verificati nel codice.)*
7. **Conteggi senza una riga che li riconcili**: 597, 372, 223 e 64, 142, 158, 241. E "indicatore", "serie", "dataset" e "scheda" si alternano come sinonimi. (Il primo giro aveva già visto 597, 372 e 67.)
8. **Acronimi non spiegati o interni**: "DISET" nel testo pubblico (il `CLAUDE.md` del progetto vieta l'acronimo interno nudo); "BES" mai sciolto in "Benessere equo e sostenibile" nel testo visibile.
9. **Fatti scritti a mano che possono uscire di sincronia**: "dodici dimensioni" (imprecisa per le province, due non hanno dati), "sei tentativi", "dieci coppie", "dieci secondi", e ogni cifra nei ritratti delle regioni, che il modulo stesso dice "non si ricalcola da sola".
10. **Una promessa di fiducia non vale ovunque**: `/metodologia` dice che ogni scheda con spiegazione causale "porta accanto una citazione verificata di un'istituzione"; nel campione di 10 schede, tre hanno una spiegazione causale con `fonti: []`. È un minimo, non una stima.

### Errori di messaggio nei giochi (da audit)

- **Gli stessi eventi hanno parole diverse**: "La riapriamo da capo" contro "La riprendiamo da capo" (riprendere è continuare); "scaduta" ha due sensi (sessione di 12 ore e timer di dieci secondi); "Troppe risposte/tentativi/richieste" tre sostantivi per lo stesso blocco.
- **Prima persona maschile**: "Non sono riuscito ad aprire la sfida", mentre il resto del sottomarchio parla alla seconda persona.
- **Messaggio generico che nasconde un costo**: "Qualcosa non ha funzionato. Riprova." In serie, `docs/GIOCO.md` avverte che "Riprova" dopo una risposta persa azzera la serie.
- **Gergo e falsità**: "La sessione di gioco non è più valida" (gergo), e `score_missing` ("Rispondi almeno a un round...") che per il codice vale anche "sessione non plausibile": chi ha risposto a dieci round legge un messaggio falso.
- **"Risposta non valida"**: contiene una parola che NN/g indica come accusatoria.
- **Stonature di tono**: "Hai indovinato!" in un sottomarchio dichiarato senza coriandoli; "Lazio è sbagliata" dove è la scelta a essere sbagliata ("Non è il Lazio").
- **Condivisione**: "La sfida condivisa: 7 su 10. Riesci a superarla?" non dice di che gioco né che livello e timer possono differire; il testo copiato ha una riga di simboli senza legenda.
- **La pagina di Ordina** descrive livello e quantità in modo diverso dal client.

### Che cosa va bene e non si tocca

Il blocco "Che cosa questo controllo non garantisce" in metodologia; le note sul limite specifiche del dato (per esempio "Chi dorme in una seconda casa, da parenti... non lascia traccia"); l'onboarding di Ordina ("Ordina dal valore più alto al più basso. Non dal risultato migliore al peggiore"); "La partita si è interrotta, non per colpa tua"; la nota onesta di Dov'è la provincia? ("Non è equivalente alla partita sulla mappa e non facciamo finta che lo sia"); il "tu" del quiz. Le definizioni a una riga con "che cosa è, che cosa non è".

## 3. Che cosa dice l'evidenza (verificata dove indicato)

- **Non esistono soglie ufficiali** su lunghezza dei testi (Google dichiara di non avere un word count preferito) né una soglia Gulpease universale. Come obiettivo di lavoro, 60 o più per i testi per tutti e 40 o più per quelli di metodo (scelta dichiarata, non una regola). L'indice si ricalcola con cautela: dove le liste non hanno punto finale il numero è falso (per `/metodologia` la cifra grezza era 40, il ricalcolo dell'audit sulla sola prosa dà circa 55).
- **Il limite del dato va in testa quando cambia le conclusioni, e dice che cosa si può fare con il numero.** Le avvertenze generiche non aiutano (guida del Government Analysis Function britannico: "Phrases like 'care must be taken'... are not sufficient").
- **Una pagina di metodo non crea fiducia da sola** (Reuters Institute: l'effetto della trasparenza è misto e più forte in chi già si fida). Serve soprattutto a chi cita: dichiarare chi risponde, da dove arrivano i numeri, che cosa il metodo non garantisce, come si segnala un errore.
- **Divulgazione progressiva, non oltre due livelli** (NN/g); **piramide rovesciata**; le persone scorrono più che leggere (dati NN/g datati: usarli come ordine di grandezza).
- **Tutorial iniziali**: aiutano poco, costano attenzione (NN/g). Tre righe al punto d'uso battono un tutorial a schede.
- **Errori**: non accusare, offrire un rimedio (NN/g). **Tooltip**: mai la sola sede di una definizione essenziale (NN/g).
- **Un esempio di metodo trasparente di un concorrente** (verificato): Lab24 dichiara che 1.000 punti vanno alla provincia con il valore migliore e 0 alla peggiore, per ciascuno dei 90 indicatori, con il "senso di lettura" definito dalla redazione. È una frase corta che dice che la scala è una scelta editoriale: il nostro z-score orientato dice lo stesso in modo più rigoroso ma in un posto meno raggiungibile.
- **Non provato**: l'effetto delle serie e della perdita sulla permanenza nei giochi (le cifre in giro vengono da blog), l'effetto del titolo-tesi sulla comprensione (fonti accademiche non lette).

## 4. SEO: i testi di guida contano poco, e conviene dirlo

| Intervento | Impatto SEO atteso | Motivo |
| --- | --- | --- |
| Riassunto in testa a `/metodologia` | basso sul traffico, medio sulla citabilità | nessuna query con volume; serve a chi cita |
| Definizione più asciutta nelle schede ad alto volume (PIL pro capite, livello di istruzione) | medio | è la pagina che già si posiziona a 14-18 per 2.400-3.600 ricerche; il testo di guida aiuta solo se coincide con la domanda di una pagina che ha dati propri |
| Pagine di glossario separate | basso | nessun termine tecnico del sito ha volume noto, e il confronto è con Wikipedia e Istat |
| FAQPage o HowTo | nullo | Google ha spento i rich result FAQ il 7 maggio 2026 (verificato) |
| Messaggi di errore, giochi | nullo sul traffico | usabilità e fiducia |

Rischi SEO reali: il blocco di spiegazione ripetuto uguale su centinaia di schede (non è dimostrato che Google lo penalizzi, ma ogni scheda deve restare distinta dai suoi numeri: la spiegazione lunga vive una volta in `/metodologia`, la scheda porta una frase e un link); un testo che regala la risposta nel gioco; una metodologia troppo lunga senza riassunto.

**"Come si calcola il tasso di disoccupazione"** ha 70 ricerche al mese, il sito è in posizione 39: anche in prima pagina varrebbe poche visite. Non è una ragione per scrivere un glossario.

## 5. Come dovrebbero essere scritti: i criteri

Cinque criteri per tutti, poi uno per tipo di testo. Ogni criterio ha esempio buono e cattivo, presi dal sito, nell'audit (`studio-guida-audit/lavoro/RAPPORTO.md`, sezione 8).

**Per tutti:**
1. **Una parola, un significato.** Se "profilo", "serie", "classifica", "scaduta" ne hanno due, uno cambia nome.
2. **Una cifra che il codice conosce non si scrive a mano.**
3. **Nessun gergo di sistema** nel testo per il lettore: sitemap, token, sessione, seed, acronimi interni.
4. **La promessa e il limite nello stesso blocco**, non in due pagine.
5. **Voce**: impersonale o "noi" nelle pagine dell'atlante, "tu" nei giochi, mai la prima persona singolare.

**Per tipo:**
- **Intro di pagina**: che cosa c'è, per chi, che cosa si può fare. Prima il significato, poi la cifra. Una idea per frase.
- **Come leggere**: un esempio con l'unità vera e il verso, un solo limite specifico del dato. Non una frase che vale per ogni percentuale.
- **Definizione** (popover): al massimo trenta parole, che cos'è e che cosa non è, senza cifre. Stessa parola, stessa definizione ovunque, il link porta a un'ancora che la contiene.
- **Nota sul limite**: specifica del dato, nella frase sua. Niente "va letto insieme ad altri indicatori".
- **Metodologia**: ordine per bisogno del lettore (riassunto di cinque righe, fonti, calcolo, che cosa non garantisce, errori e correzioni, come citare), non per storia del progetto. Elenchi lunghi chiusi.
- **Onboarding del gioco**: al massimo tre regole, nell'ordine in cui servono, numeri da costante.
- **Errore**: che cosa è successo, di chi non è la colpa, che cosa fare. La stessa formula per lo stesso evento in tutti i giochi.
- **Esito**: un fatto, non un giudizio. **Condivisione**: chi riceve capisce in una riga che cosa è e come si fa, senza spoiler e senza simboli senza legenda.

## 6. Priorità, costo, rischio

Costo in file toccati, non in ore. Ogni testo di v1 ha un **gemello di ripiego** (`methodology.html`, `indicator_page.html`, `region_page.html`...) e una **variante Markdown** per agenti (`app/agent_discovery.py`): cambiare un testo vuol dire cambiarlo in due o tre posti. Ogni modifica a `frontend/src/` richiede `npm run build` e i test `node --test`.

**Prima una decisione di Nello**, perché tutto il resto ne dipende: la **regola di nome** per indicatore, serie, scheda e dataset, con una riga che riconcili 597 e 372, e se la sezione "Come leggere un numero" in `/metodologia` diventa la casa unica delle definizioni. Se si scrive prima, va riscritto dopo.

**PR 1, testo, nessuna build frontend (circa 6 file, 2 test da rileggere):**
- Definizioni in `/metodologia` (media semplice, verso, n.d., copertura, posizione media, percentile, punteggio, ripartizione, profilo) con ancore; i popover e i link "Come si calcola" puntano alle ancore. Le ancore esistenti non si spostano.
- Riassunto di cinque righe in testa alla metodologia.
- Togliere "DISET" dal testo pubblico, sciogliere BES alla prima occorrenza.
- Correggere "dodici dimensioni" per le province (una riga di `quality_life_config.py`).
- Riscrivere il blocco "Come è calcolato" della scheda, e la frase "classifica del BES" in `regioni.html:90`. È il blocco più bloccato dai test (`test_quality_life.py:94`, `test_transparency.py`): rischio medio-alto.

**PR 2, giochi, solo testo, con `npm run build` (circa 7 file frontend e 4 template):** "va in classifica" in Chi è maggiore? (il testo del client è quello che il server manda come avviso: i due restano uguali); lead di Indovina la Regione; la parola "stima" nelle distanze di Indovina la Provincia; un solo lessico per gli errori, al femminile o impersonale; "scaduta" e "riapriamo/riprendiamo"; il 503 anche negli altri giochi; "Hai indovinato!" e "è sbagliata"; testo di condivisione con legenda; pagina di Ordina allineata al client. Va provato in un browser, anche su telefono: nessun worker l'ha fatto.

**PR 3, codice (circa 4 file e un test nuovo):** pagina 500, errori su "Esporta" ed "Elimina account", frase su che cosa dà un account. Un handler 500 non deve mai sollevare a sua volta, e il template nuovo è `noindex` come la 404.

**P1 e P2, uno alla volta:** definizioni nelle didascalie della pagina regione ("In media la Puglia è 14ª su 20 regioni" spiegata in una riga); stati vuoti senza uscita (tema, province); una guardia di test che leghi i testi dei giochi alle costanti; la 404 con ricerca; la promessa causale di `/metodologia`, da misurare su tutte le schede e poi correggere o la frase o le schede (**decisione di Nello**); i dieci passaggi più pesanti per leggibilità.

**Da non fare ancora:**
- Riscrivere in blocco i 388 "Come leggere il dato". `docs/AUDIT_VOCE.md` conclude che l'uniformità è consistenza voluta. Interventi mirati dopo aver contato quante schede usano la frase vuota "nel gruppo di riferimento definito dalla fonte".
- Un glossario in pagina separata prima che le definizioni abbiano una casa in `/metodologia`: sarebbe la settima formulazione di "media semplice".
- Cambiare ancore, URL o il nome `/quiz`.
- Cambiare le etichette di `app/sources.py` per sciogliere BES: compaiono su decine di pagine.
- Unificare i tre sensi di "serie" cambiando i contatori: solo le etichette.
- Aggiungere il livello al frammento della sfida condivisa come "correzione di testo": cambia che cosa viaggia nell'URL.
- Descrivere nei testi le difese anti-barare: il repository è pubblico.
- Riscrivere i ritratti delle regioni: prima una guardia di vintage.
- Pubblicare di nuovo la riga sull'articolo 50 del regolamento europeo sull'IA in una forma nuova senza verificarla su fonte primaria: è già nel sito e nessuno l'ha verificata.
- Aggiungere markup FAQPage o HowTo: i rich result non esistono più.

## 7. Raccomandazione

Una decisione di Nello, poi tre PR nell'ordine 1, 2, 3. Non cominciare dai dieci passaggi di leggibilità né dalla home: sono i più visibili e i meno urgenti, e se si fanno prima della regola di nome vanno rifatti. L'impatto SEO atteso dai testi di guida è basso: lo scopo è fiducia, comprensione e un gioco i cui messaggi non dicono cose false.

## 8. Verifiche eseguite sul sito (1 ottobre 2026)

Un worker ha eseguito le affermazioni degli studi sul render reale (client di test Flask, 576 URL del sitemap, dati locali, nessun segreto). Ho ricontrollato di persona: nessuna "media semplice" in `/metodologia`, il title senza accento di `ter-920`, le due meta robots di `/account`, gli apostrofi in `content/indicators/901.md`.

**Confermato:**
- La ricerca senza risultati mostra il messaggio, con i link a temi, regioni e province (smentisce il worker evidenza).
- **Pagina 500**: risposta di Werkzeug, 265 byte, `lang=en`, senza navigazione né link di uscita, anche per `/atlante` quando la regia cede. Il ripiego delle altre pagine è invece un 200 silenzioso con il vecchio template e il vecchio title.
- **H2 di menu**: 4 nell'header e 4 nel footer, e il documento apre con un `h2` prima dell'unico `h1` (su 15 pagine, un solo `h1` ciascuna).
- **Popover**: quattro su cinque portano a `/metodologia` senza ancora, e "media semplice", "verso", "n.d.", "copertura variabile" non trovano la loro definizione. La metodologia non contiene "media semplice", "n.d.", "posizione media", "percentile".
- **`Eta media`**: vale solo per l'id 920. Viene dal CSV legacy `Assoluti_Regione.csv`: `scripts/build_external_dataset.py` lo rigenera, quindi correggere solo il manifest o il normalizzato non basta, l'errore tornerebbe. Anche "Definizione della fonte" e "in eta feconda" restano senza accento.
- **Conteggi**: 597, 372, 223, 64, 142, 158, 241, 67, 107, 20, 12 sono tutti calcolati e coerenti col dato, salvo `app/nav.py:33-34` e `divari_regionali.py:119` scritti a mano e un docstring in `app/divari.py` che dice 221 invece di 241. Il 142 di metodologia e quello di regione sono due calcoli diversi con lo stesso valore, senza un test che li tenga allineati.
- **"Dodici dimensioni"**: vero per le regioni, falso per le 107 province (dieci). La classifica province lo dice, ma `/metodologia` dice "dodici categorie... per entrambi i livelli" (righe 172 e 208).
- **Promessa causale**: 292 schede su 383 hanno `fonti: []`, 29 contengono espressioni causali (euristica); su 12 lette a mano, 8 sono spiegazioni vere. La promessa di `/metodologia` è smentita almeno per 25-29 schede.
- **Frasi vuote**: "nel gruppo di riferimento definito dalla fonte" compare in 128 schede su 388 e "Il dato va letto insieme a unità di misura, anno e copertura" in 57. Insieme 185 su 388, il 47%.
- **Link interni**: 28 pagine, 4.122 link, 1.569 URL distinti, tutti 200, nessuna ancora mancante.
- **Etichette**: ogni destinazione ha da 2 a 5 etichette diverse nella stessa pagina (la home ha 5 modi di dire `/qualita-della-vita`, 5 per `/blog`, 7 per `/atlante`).

**Smentito:**
- Lo spazio in "7 ª" non esiste nel DOM: `<data>7</data><span class="n__o">ª</span>`, è un artefatto dell'estrazione del testo.
- La didascalia "Punteggio da 0 a 100" non è doppia: l'etichetta è il bottone e la frase lunga è il popover adiacente.

**Misure nuove (rispondono a ciò che lo studio dei title non sapeva):**
- Su 576 URL: **1** title sopra 60 (l'atlante), **19** meta sopra 155 (home, atlante, province, privacy, 8 province su 107, 7 articoli su 17), **170** meta sotto 110 (164 schede su 388, il 42%, 5 regioni, il catalogo), nessun title o meta duplicato. Le meta più corte sono di 33, 36 e 39 caratteri, e 65 schede stanno sotto 80.

**Altri difetti trovati dal worker, non citati prima:**
- `/account` ha due meta robots in conflitto: `index, follow` dal template base e `noindex, nofollow` da `account.html:6`.
- La scheda `ter-901` (PIL pro capite, la più vista) ha apostrofi al posto degli accenti nel testo (`e'`, `piu'`, `Il Lazio e' quinto`), nel file `content/indicators/901.md`. È l'unica pagina su 577 con questo schema.

**Suite di test.** Non si può eseguire in un solo processo: l'interprete (Python 3.13.12 nel venv locale, il Dockerfile usa 3.12) va in segfault in almeno 7 test e moduli. Eseguita modulo per modulo: 127 moduli, 1.906 test eseguiti, 6 moduli in segfault (non contati), fallimenti per `requests` mancante nel venv (`test_foto_autore`, `test_verify_pezzi_trend`, il gruppo trend articoli), e quattro moduli (`test_app`, `test_atlante`, `test_editoriale_guardia`, `test_indicator_view`) che hanno fallito nel ciclo ma passano rieseguiti da soli, tranne `test_app` che resta instabile. Nessun verdetto pulito è possibile senza Python 3.12 e `requests` nell'ambiente.

## 9. Verifiche nei giochi, nel browser (1 ottobre 2026)

Un worker ha giocato i cinque giochi con Chromium a 375 e 1280 px, sulla sfida n. 79, con localStorage pulito e con rete simulata assente, abortita e in 503. Ho ricontrollato uno screenshot e due difetti nel codice (`order.jsx:671-673`, `leaderboard.jsx:163`). Gli screenshot (65) stanno nel worktree `verifica-giochi`, fuori dal ramo. **Nessun overflow orizzontale a 375 px**, nessun testo in inglese, nessun bottone senza etichetta.

**Affermazioni dell'audit: 12 confermate, 1 smentita, 1 smentita in parte.**
- **Smentita nei fatti:** "con i dieci secondi la partita va in classifica". La sfida del giorno a tempo non ha nessuna classifica (a fine partita non compare né un invito né un nickname, nessuna chiamata alla classifica). La classifica è delle "migliori serie", cioè dell'allenamento a serie. Il testo promette una cosa che non esiste: il difetto resta, ed è quello che l'audit chiamava ambiguità.
- **Ordina, in parte:** la frase "tre regioni per iniziare, cinque per la sfida completa" è vera nel client. Non coincidono invece l'onboarding del client ("Trascina la maniglia o tocca due volte. Le frecce spostano una riga alla volta") e quello della pagina ("toccando una regione e poi la posizione"), e "livello" vale cose diverse (Regioni / Stessa regione / Province nel client, 3 o 5 nel testo).
- **Confermati con testo letterale:**
  - Il lead di Indovina la Regione promette "più vicino o più lontano", ma a schermo ci sono solo "più alta/più bassa della misteriosa", la posizione in graduatoria e, dal terzo errore, la ripartizione, mai spiegata (Nord, Centro, Mezzogiorno non compaiono).
  - Indovina la Provincia dice "Circa 77 km verso sud-est" senza la parola "stima", né in partita né in pagina, solo "approssimati". Dov'è la provincia? la dice, ma con una virgola davanti ("a circa 298 km a sud-ovest, stima").
  - Esiti: "Tentativo 1: Lazio è sbagliata" (in Provincia: "Teramo non è la provincia"), "Hai indovinato!". Al termine, tre frasi per lo stesso esito: "Hai indovinato!", "Giusto.", "Indovinata al primo tentativo".
  - Condivisione: solo `●` e `○`, nessun triangolo, senza legenda. In Dov'è la provincia? i cerchi sono su 10 domande ma il punteggio su 20. Il link di sfida condivisa nasce solo da Chi è maggiore e da Dov'è la provincia?; in Regione, Provincia e Ordina l'hash non fa nulla. Il box "La sfida condivisa: 7 su 10. Riesci a superarla?" non nomina il gioco né il livello, e con un numero di sfida vecchio sparisce senza avviso.
  - Onboarding: solo Regione e Provincia hanno un modale "Come si gioca" (3-5 righe); gli altri mostrano un blocco di regole fisso. Nessun tutorial interattivo. La sfida del giorno è chiaramente quella principale, ma "le statistiche contano solo la sfida del giorno" sta solo nel modale delle statistiche.
  - Quattro nomi per la stessa sezione: "Sfida Italia", "Quiz", "Quanto conosci l'Italia?", "Classifica". "Serie" vale almeno quattro cose, e "giorni di fila" ha due definizioni che si contraddicono (hub: "con almeno una sfida"; statistiche: "in cui hai vinto la sfida del giorno").
  - Senza JavaScript: Regione, Provincia, Chi è maggiore, Ordina e Mappa mostrano il lead e un fallback; l'hub e la classifica no, restano "Caricamento delle statistiche...". **Con il bundle bloccato** (JS attivo) il fallback non copre: resta "Preparazione della sfida del giorno..." per sempre, senza errore e senza link.
  - La 404 di un gioco è la pagina generica, senza rimando a `/quiz`.

**Errori di rete, il risultato più utile.** In **Chi è maggiore?** con rete assente il giocatore resta per 3-8 secondi con A e B disabilitati, senza messaggio e con il timer sparito, poi compare "Non riesco a raggiungere il server. Riapri la sfida di oggi.". In **Indovina la Provincia e Regione** l'errore è un generico "Il tentativo non è andato a buon fine. Riprova." **senza bottone**. In **Mappa e Ordina** è "Qualcosa non ha funzionato. Riprova." e la Mappa non ha un bottone "Riprova". Ordina ha un solo messaggio per tutto, anche per il token non valido. Dopo "Riprova" in allenamento la serie **non** si azzera: l'avviso di `docs/GIOCO.md` va riletto contro il comportamento reale. Il 429 si legge in tre modi ("Troppe risposte/tentativi/richieste") e in Regione non c'è (il generico).

**Difetti nuovi, non citati dall'audit:**
1. **Ordina, tastiera: i bottoni ▲ ▼ non rispondono a Invio o Spazio.** La riga cattura Invio e Spazio e il tasto del bottone risale fino a lei. Con il mouse funzionano, con la tastiera no, e "le frecce spostano una riga alla volta" non è vero. Da testo promesso, un problema di accessibilità, non solo di copy. È codice, non testo.
2. **Grammatica**: "Stai vedendo i punteggi dei ultimi 7 giorni" e "dei tutti i tempi" in classifica (`leaderboard.jsx:163`, la stringa composta con il periodo); "Il tuo risultato: 1 risposte di fila" (singolare sbagliato in Chi è maggiore); "Risultato parziale." come titolo di una partita finita; "tra" in Regione e "fra" in Provincia.
3. **Mappa**: i venti gruppi delle regioni hanno `aria-label="Regione"` e le province `aria-label="Provincia"` (da verificare con un lettore di schermo vero); il riepilogo "1 provincia esatta, 0 nella regione giusta" con "2 su 20" non si legge senza conoscere la regola (esatta 2, regione giusta 1).
4. **Bersagli tattili a 375 px**: Valle d'Aosta misura 26x17 px nella mappa di Regione, Molise 28x22; link inline di fine partita da 15 a 21 px. I bottoni di gioco veri sono tutti da 44 px o più.

**Cosa va aggiunto alla proposta (PR 2, giochi):** il messaggio durante il silenzio di rete di Chi è maggiore; i bottoni "Riprova" mancanti in Regione, Provincia e Mappa; il 429 anche in Regione; un'uscita per il bundle non caricato; la frase del box di sfida condivisa con nome del gioco; la legenda dei simboli e il perché dei cerchi su 10 con punteggio su 20 nella condivisione; l'allineamento del testo server di Ordina al client; il rimando ai giochi nella 404 di `/quiz/*`. **Da decidere con Nello:** la tastiera di Ordina (una correzione di codice che merita una PR e un test a sé).

**Non verificato:** "La riapriamo da capo" della Mappa e di Chi è maggiore a schermo (serve un token superato dopo una ripresa vera; provato solo per Provincia con una risposta finta); sfide passate e archivio; lettore di schermo vero; contrasto misurato (solo a occhio); `navigator.share` nativo.

## 10. Competitor, rifatti con citazioni controllate (1 ottobre 2026)

Secondo giro, con un worker Claude (sonnet) in sola lettura. Le citazioni segnate **letterale** sono estratte con `curl` dall'HTML; quelle segnate **WebFetch** passano da un modello piccolo e vanno ricontrollate prima di citarle altrove. Non ho riverificato di persona ogni frase.

**Che cosa si può dire.**
- **Lab24** dichiara verso e peso: "mille punti vengono dati alla provincia con il valore migliore e zero punti a quella con il peggiore, in base ad un 'senso di lettura' del parametro ... definito dalla redazione", e la classifica è "la media aritmetica semplice delle sei graduatorie di settore". Bene: un metodo solo, scala chiara, fonti nominate per istituzione. Male: "senso di lettura" è gergo e la spiegazione sta in una nota in fondo, non accanto al dato.
- **Noi Italia (Istat)** apre con una promessa al lettore, "100 statistiche per capire il Paese in cui viviamo", e elenca che cosa contiene (sei aree, diciannove settori, glossario, download). Male: una frase d'apertura di circa 40 parole e un testo segnaposto "Donec id elit..." rimasto in pagina.
- **IstatData** mostra errori generici in inglese ("An error occurred while contacting the server."). Il 404 di Istat è un menù senza una frase che dica dove andare.
- **Our World in Data** dice subito chi scrive e chi finanzia, e le FAQ sono domande vere in ordine di dubbio (fiducia prima, riuso dopo). Male: "more on our mission below" rimanda a una risposta che non c'è.
- **Openpolis** e **Tuttitalia** nella parte letta non hanno metodologia in homepage: lo slogan o la promessa ("Guida ai Comuni...") prende il posto della spiegazione. Giudizio provvisorio.
- **Truenumbers**: titoli con cifra e conclusione ("Tetto del 30% agli studenti stranieri: il divario non c'è"), da copiare per gli articoli, non per le schede. Una pagina inesistente dà un 403 muto.

**Che cosa non si può dire.** Truenumbers solo in homepage, Eurostat Regional Yearbook non raggiungibile (login), nessun altro atlante regionale. Non esiste evidenza competitor su regole, errori o condivisione dei giochi: nessun concorrente letto ha giochi, e le correzioni sui giochi poggiano solo sul nostro codice.

**Cinque indicazioni di scrittura che ne escono.**
1. Dichiara la scelta editoriale dove sta il numero, non in una nota in fondo. Divario ha tre metodi con lo stesso nome "punteggio": un nome per metodo.
2. Scrivi una promessa al lettore, non una descrizione di ciò che fa il sito.
3. Ordina le FAQ come domande vere, dalla fiducia all'uso. Ogni termine che un popover manda a `/metodologia` ha la sua definizione lì.
4. Una parola sola, "indicatore" (decisione di Nello del 1 ottobre): nessun competitor ne usa una in modo coerente, quindi non c'è uno standard da seguire, solo da fissare.
5. Gli errori dicono che cosa è successo e che cosa fare, nella lingua del sito, e dicono il costo ("Riprova" azzera la serie).

## 11. Che cosa non sappiamo

- **I giochi sono stati provati nel browser** (sezione 9), ma da un worker automatico, non da giocatori. I percorsi delle quattro persone sono inferenze dal testo, non osservazioni di utenti. Nessun dato di scorrimento o permanenza.
- **Gli errori dei giochi sono stati simulati** (rete assente, 503, 429, token non valido), non osservati in uso reale.
- **Il campione di `content/`** è di 10 schede e 5 articoli su circa 383: quello che dice vale per il campione.
- **Competitor**: rifatti nella sezione 10, ma sui giochi degli altri non c'è evidenza (Wordle e NYT bloccano la lettura) e alcune citazioni restano da WebFetch, non letterali.
- **Fonti accademiche** sui titoli-tesi, sulla comunicazione dell'incertezza e sulle serie nei giochi non sono state lette.
- **Articolo 50 del regolamento IA e rapporto della Banca d'Italia sulla Calabria**: citati dal sito, non verificati.
- **La suite di test non dà un verdetto pulito** (sezione 8): le asserzioni che bloccano i testi sono cercate per stringa.
- Il rapporto dell'audit non è stato riletto da una seconda persona.

## 12. Che cosa è stato fatto (1 ottobre 2026)

Decisione di Nello: la parola pubblica è "indicatore". Tre PR aperte, non ancora in master:
- **#308**, testi di `/metodologia` e della scheda: riassunto, dieci definizioni con ancora, "DISET" tolto, "dodici" corretto, blocco "Come è calcolato" riscritto.
- **#310**, giochi: lessico unico degli errori, Riprova dove mancava, tastiera di Ordina, "va in classifica" tolto. In allenamento "Riprova" azzera il contatore a schermo come fa il server.
- **#309**, pagina 500 in italiano e messaggi su Esporta ed Elimina account.

Restano fuori, da decidere: il blocco "Come nasce questa scheda" (tre test lo fissano), il catalogo dati che dice ancora "dataset", la promessa "citazione verificata" contraddetta da 292 schede senza fonti, `.account-danger:hover` con `var(--error)` non definita, i bersagli tattili della mappa a 375 px, la 404 di `/quiz/*`.
