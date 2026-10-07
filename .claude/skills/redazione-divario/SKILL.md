---
name: redazione-divario
description: Scrivere, riscrivere o rivedere un testo di Divario Italia, cioe un articolo del blog (content/posts) o il testo di una scheda indicatore (content/indicators), con grafici e immagini. Usala sempre quando il compito e produrre o correggere prosa del sito, preparare un brief o uno scout, fare da revisore di un pezzo, scegliere un argomento da una query di Search Console, o controllare che un testo non sembri scritto da un'IA, anche se nessuno nomina la pipeline.
---

# Redazione di Divario Italia

## Prima distinzione: blog e scheda indicatore
Il **blog** parte da un fatto e da una domanda reale del lettore; gli indicatori interni sono base e un tassello, mai la tesi. Vietata una tesi fondata solo sulla correlazione fra indicatori interni. Servono almeno tre fonti esterne autorevoli, aperte e verificate con URL e data, e un grafico che integri dati esterni. **La scheda indicatore** spiega un indicatore; gli altri danno solo contesto. Per entrambi, privilegia dati recenti e dichiara ultimo anno/periodo osservato e data della fonte. Il Gate A v3 e i suoi campi sono definiti in `docs/design_drafts/team/PIANO.md` e `/mnt/c/Users/Nilo/orca/specs/REDAZIONE-divario-v3.md`; la spec esterna possiede il formato del report. La v3 prevale sui passaggi v2 rimasti sotto.

Un testo del sito nasce da una domanda vera di chi cerca e da dati con fonte e anno, passa per ruoli separati e arriva al titolare come bozza. Le regole qui sotto vengono da errori reali: il pilota carceri del 28/09 (testo "molto grezzo", titolo su un estremo non verificato), il pilota ter-12 (cinque frasi che dicevano una cosa diversa dal dato mentre la guardia numerica era verde), una bozza scritta senza pipeline il 4/10 (definizioni infedeli, "il quadro non cambia" falso, link mancanti). Leggi anche `content/STYLE.md` (le regole tipografiche sono vincolanti) e, per le schede, `docs/INDICATOR_PAGES.md`.

## 0. Redazione v2 (7 ottobre 2026): storico, non operativo
Il titolare ha bocciato il pezzo dei medici di famiglia: «troppo numerico, nessun vero insight, non tiene conto di tutti gli indicatori». Questo blocco registra la decisione v2, sostituita dalla v3 descritta in apertura. I requisiti v2 non sono più operativi.
- **Scout e brief**: i passaggi v2 sotto sono superati dalla distinzione blog/scheda e dal Gate A v3.
- **Gate A**: non richiedere più l'incrocio di tre indicatori interni come tesi obbligatoria del blog.
- **Grafici**: non limitare le figure del blog ai dati interni.
- **Scout multi-indicatore** (§2): il dossier copre tutti gli indicatori dello stesso tema e dei temi vicini (`app.indicator_universe`), con `copertura.csv`; non si scrive su un solo indicatore.
- **Gate A «insight»** prima dello scrittore: il brief dichiara domanda del lettore, tesi in una frase, almeno un insight non ovvio e tre indicatori incrociati; lo giudica un caporedattore di famiglia diversa (Astra, un giro, riga nel battito) in `lavoro/<chiave>/gate-a.md`. Senza PASSA lo scrittore non parte.
- **Gate B «racconto»** in revisione (§6): tesi sostenuta, confronto fra due territori reali, significato concreto per il lettore nei primi due paragrafi, risultato non ovvio con controllo contrario; voto 1-5, sotto 4 si riscrive, due giri al massimo, in `lavoro/<chiave>/gate-b.md`. Persone solo da fonti citate, mai inventate.
- **Grafici** (§5): solo il generatore standard (`scripts/trend_articles/figures.py`) per il blog, mai disegni scritti a mano; si guardano nella bozza HTML.
- **Bozza HTML** (§6) prima del merge, e il merge solo con l'ok della direzione.
Le sezioni 1-7 qui sotto restano valide per quanto non contraddicono questo blocco; dove il divieto «nessun nome di persona» si scontra con il racconto, vale: persone solo da fonti citate, mai inventate o composite.

## 1. Il filo, prima di tutto
Per il blog scegli un fatto attuale e una domanda reale (Search Console: `searchAnalytics` per `page` e `query`, 28 giorni); verifica angoli e fonti prima di fissare una tesi. Per una scheda parti dalla misura del suo indicatore. Controlla che non esista gia un articolo sul tema (`content/posts`) e non ripeterlo.

## 2. I ruoli, uno alla volta, di famiglie diverse
dossier (`bin/py -m scripts.editoriale.brief <codice> --out lavoro/<chiave>/dossier-<codice>.json`, usato per tutte e due i pilota del blog. Esiste anche `scripts.trend_articles.dossier` per la catena dei trend di `docs/WORKFLOW_ARTICOLI_TREND.md`, non serve per i pezzi nuovi) poi scout, brief del leader, scrittore, grafico, revisore. Il revisore e di un'altra famiglia di modelli dello scrittore, perche un modello rilegge male cio che ha scritto lui. Un worker alla volta, ogni passo in un commit. `lavoro/` e escluso in locale: `git add -f`. Il lancio dei worker, i giri di review e il merge stanno nella skill `lancio-e-cancello-divario`.
- **Scout**: per il blog scrive `fonti.md` con almeno tre fonti esterne autorevoli, aperte e verificate: istituzione, data, URL, citazione letterale e limite d'uso. Cerca il dato osservato più recente e possibili angoli; non decide tesi. Per le schede raccoglie fonti per l'indicatore e contesto. Voce senza fonte: "non trovato", mai riempita. Una causa regionale senza fonte non esiste.
- **Brief**: lo scrive il leader come materiale, non scaletta: domanda, angoli giornalistici verificati, tesi in una frase, dati verificati con anno e data della fonte, fonti ammesse, "cose da non scrivere" e lezioni dei pezzi precedenti. Dichiara il ruolo base degli indicatori interni. E l'unico input numerico dello scrittore.
- **Scrittore**: legge solo brief, fonti, dossier, STYLE.md e un solo modello di voce (`content/esempi/lavoce-salari-sud.md`). Non copia la struttura di altri pezzi.
- **Grafico**: vedi sezione 5.
- **Revisore**: sola lettura, rilievi numerati R1, R2... con gravita e la frase.

## 3. Numeri: ogni frase che cita un dato, contro il dato
La guardia numerica (`scripts/editoriale/guardia.py`, solo schede) vede le cifre, non il senso. Il revisore controlla il senso di OGNI frase con un numero, un confronto, un posto, una direzione ("sale", "tutte", "primo", "sorpasso"). Casi che hanno gia morso:
- Un tasso non e un numero assoluto. Il periodo non e il totale (il tasso di fecondita e di un anno di calendario, non i figli che le donne avranno).
- Le differenze fra due regioni si calcolano dai valori non arrotondati. Il rapporto fra due grandezze di natura diversa (PIL e reddito) e un confronto, non una quota.
- I posti seguono il sito (ordinali: Lombardia 5, Veneto 6), non i pari merito. Il testo dice "stesso valore" se serve.
- Il Trentino-Alto Adige e un aggregato di due province per l'Istat: dirlo se si cita Bolzano o Trento, con la fonte e l'anno giusti.
- Un evento datato (un sorpasso, un minimo) su un margine di un centesimo o su stime provvisorie va detto con la sua fragilita.
- Nessuna causa senza fonte. "i dati mostrano il posto, non la causa" e una frase sua.
- Una correlazione citata va misurata e detta in parole semplici (sulle venti regioni, lineare, su un massimo di 1).
- Un dato esterno va registrato con fonte, URL e data; il documento citato deve contenere l'anno del dato (un PDF del 2026 non contiene il 2024 provinciale: e successo nel pilota 2).

## 4. La lista "non IA" (e la lista del revisore)
**Apertura = un messaggio, in parole comuni.** La prima frase dice il messaggio come lo ripeterebbe a un amico un lettore non esperto, con al massimo un numero per frase e nessun termine tecnico (PIL, reddito disponibile, tasso, definizioni Istat) nei primi due paragrafi: i termini si spiegano dal terzo. Vale per titolo, sommario e primi paragrafi. Nasce dal feedback del titolare sui due pilota del 5/10 ("corretti, ma l'apertura e ancora articolata e tecnica").

Domanda reale e dato con fonte e anno nel lead. Una tesi nel titolo. Esempi territoriali concreti, un ancoraggio con due regioni. Nessuno schema fisso a sezioni (le H2 sono narrative e diverse da un pezzo all'altro). Niente apertura generica, niente chiusura che riassume ("In conclusione", "In due righe"). Niente formule da IA (cruciale, panorama, tessuto, "e importante notare", "in un mondo in cui") e niente elenchi puntati superflui. Frasi di lunghezza varia con qualche frase corta, un'idea per frase, il caveat prende la sua frase. Non scrivere il numero due volte nella stessa frase. Niente raccordi da bot ("Torniamo a...", "Messe una accanto all'altra"). Nessun nome di persona. Tipografia: le regole di `content/STYLE.md` sono vincolanti (niente em-dash, en-dash, punto e virgola, puntini). Controllo: `grep -nP "[—–;…]" <file>` deve essere vuoto. Prosa del blog entro mille parole (tabelle e fonti escluse, come `REVIEW.md`).

## 5. Grafici e immagini: obbligatori
Ogni blog ha almeno un grafico che integra dati esterni oltre a quelli del sito e mostra la tesi giornalistica. Il dato esterno ha fonte, anno e unità nella figura; il brief e Gate A riportano variabile, periodo, URL e data della fonte. Le regole tecniche per figure e copertina restano quelle sotto: SVG dal generatore standard o script dedicato quando serve, token CSS, accessibilità, resa mobile e licenza verificata.
Ogni articolo ha anche una copertina che e una foto reale con licenza libera compatibile con l'uso commerciale (Wikimedia Commons con `photo.py`, credito nel campo `cover_credit`), pertinente al tema, senza persone riconoscibili in primo piano e mai generata con IA. Per le schede valgono i grafici dinamici già presenti: non inventare un grafico esterno quando non serve a spiegare l'indicatore.

Per i pezzi nati dal trend c'e anche `bin/py -m scripts.trend_articles.verify <file>` (frontmatter, foto, cifre del dossier, link). Sui pilota senza trend segnala errori noti di foto, dossier e trend: non e un cancello, il revisore ricalcola i numeri.

## Lunghezza (approvata dalla direzione il 6/10/2026, dati dei concorrenti in `direzione/review/concorrenti-sonnet.md`)
- **Articolo di dati**: 700-1100 parole, tetto 1100 (mediana dei concorrenti 936). Una tesi, un dato, uno o due grafici.
- **Analisi lunga**: 1400-2000 parole, al massimo un pezzo su cinque, solo se la tesi chiede metodo e confronto fra fonti.
- **Un solo conteggio**: quello di `scripts/editoriale/guardia_articolo.py`, cioe la prosa del corpo prima di `## Fonti`, senza frontmatter, tabelle e URL dei link (come la conta la guardia, `count_words`). Nessun altro conteggio vale (un altro modello contava 996 dove la guardia ne conta 1015).
- Il tetto non e un obiettivo e non e un criterio di valore: se per rientrare serve togliere un dato o una cautela, si toglie un raccordo. Sotto le 700 solo se la tesi sta in meno.

## 6. Rilievi, giri, approvazione
I rilievi vanno allo scrittore uno per uno e il leader verifica che siano tutti chiusi nel diff, non sulla parola. Massimo due giri di review (regola della direzione del 4/10, piu stretta dei tre di PIANO.md del 28/09): se dopo il secondo resta un bloccante lo decide la direzione. Il pezzo resta `draft: true` e va in una PR draft: la pubblicazione e del titolare, mai del leader. **Prima del merge la bozza si rende in HTML** (`bin/py -m scripts.editoriale.bozza_html <slug> --radice <worktree> --pr <n>`, uscita in `/mnt/c/Users/Nilo/orca/divario/bozze/` con `index.html`) e si legge li: regola del titolare del 7/10/2026, dettagli in `docs/WORKFLOW_ARTICOLI_TREND.md` §8bis. Il merge solo dopo che la bozza e nell'indice e la direzione ha scritto l'ok. Il frontmatter non porta `author` (la firma la da `config/identita.yaml`). Nessun nome di persona nei testi.

## 7. Schede indicatore
La scheda (`content/indicators/<codice>.md`) spiega l'indicatore trattato; altri indicatori sono solo contesto. Usa il contratto in `docs/INDICATOR_PAGES.md`, la guardia `bin/py -m scripts.editoriale.guardia <codice> --dossier ... --fonti ...` e lo stato in `app/editorial_state.py`. Priorita per impressioni: poche schede fanno quasi tutto il traffico, scrivi prima quelle.

## Cosa non si usa
Le skill a scheletro fisso dell'editorial-engine (in quarantena): lo schema fisso a sezioni e il primo tell di un testo da bot, e per le schede il contratto sta nei documenti del repo.
