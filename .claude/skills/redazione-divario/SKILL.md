---
name: redazione-divario
description: Scrivere, riscrivere o rivedere un testo di Divario Italia, cioe un articolo del blog (content/posts) o il testo di una scheda indicatore (content/indicators), con grafici e immagini. Usala sempre quando il compito e produrre o correggere prosa del sito, preparare un brief o uno scout, fare da revisore di un pezzo, scegliere un argomento da una query di Search Console, o controllare che un testo non sembri scritto da un'IA, anche se nessuno nomina la pipeline.
---

# Redazione di Divario Italia

Un testo del sito nasce da una domanda vera di chi cerca e da dati con fonte e anno, passa per ruoli separati e arriva al titolare come bozza. Le regole qui sotto vengono da errori reali: il pilota carceri del 28/09 (testo "molto grezzo", titolo su un estremo non verificato), il pilota ter-12 (cinque frasi che dicevano una cosa diversa dal dato mentre la guardia numerica era verde), una bozza scritta senza pipeline il 4/10 (definizioni infedeli, "il quadro non cambia" falso, link mancanti). Leggi anche `content/STYLE.md` (le regole tipografiche sono vincolanti) e, per le schede, `docs/INDICATOR_PAGES.md`.

## 1. Il filo, prima di tutto
Scegli un argomento da una query vera (Search Console: `searchAnalytics` per `page` e `query`, 28 giorni) e da un dato che il sito ha. Scrivi in una frase la tesi, verificabile con i dati: se non riesci, non c'e pezzo. Controlla che non esista gia un articolo sul tema (`content/posts`) e non ripeterlo.

## 2. I ruoli, uno alla volta, di famiglie diverse
dossier (`bin/py -m scripts.editoriale.brief <codice> --out lavoro/<chiave>/dossier-<codice>.json`, usato per tutte e due i pilota del blog. Esiste anche `scripts.trend_articles.dossier` per la catena dei trend di `docs/WORKFLOW_ARTICOLI_TREND.md`, non serve per i pezzi nuovi) poi scout, brief del leader, scrittore, grafico, revisore. Il revisore e di un'altra famiglia di modelli dello scrittore, perche un modello rilegge male cio che ha scritto lui. Un worker alla volta, ogni passo in un commit. `lavoro/` e escluso in locale: `git add -f`. Il lancio dei worker, i giri di review e il merge stanno nella skill `lancio-e-cancello-divario`.
- **Scout**: scrive solo `fonti.md`, una tabella con istituzione, data, URL aperto davvero, citazione letterale copiata dalla pagina, limite d'uso. Voce senza fonte: "non trovato", mai riempita. Cerca la definizione ufficiale dell'indicatore, il dato piu recente fuori dal sito, chi altro ne ha scritto, i limiti d'uso. Una causa regionale senza citazione letterale non esiste.
- **Brief**: lo scrive il leader come materiale, non scaletta: domanda con le query, tesi in una frase, dati verificati ricalcolati (non arrotondare in modo diverso), fonti ammesse, "cose da non scrivere", lezioni dei pezzi precedenti. E l'unico input numerico dello scrittore.
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
- Un dato esterno al sito va in `external_figures` con fonte e URL, e il documento citato deve essere quello dell'anno del dato (un PDF del 2026 non contiene il 2024 provinciale: e successo nel pilota 2).

## 4. La lista "non IA" (e la lista del revisore)
**Apertura = un messaggio, in parole comuni.** La prima frase dice il messaggio come lo ripeterebbe a un amico un lettore non esperto, con al massimo un numero per frase e nessun termine tecnico (PIL, reddito disponibile, tasso, definizioni Istat) nei primi due paragrafi: i termini si spiegano dal terzo. Vale per titolo, sommario e primi paragrafi. Nasce dal feedback del titolare sui due pilota del 5/10 ("corretti, ma l'apertura e ancora articolata e tecnica").

Domanda reale e dato con fonte e anno nel lead. Una tesi nel titolo. Esempi territoriali concreti, un ancoraggio con due regioni. Nessuno schema fisso a sezioni (le H2 sono narrative e diverse da un pezzo all'altro). Niente apertura generica, niente chiusura che riassume ("In conclusione", "In due righe"). Niente formule da IA (cruciale, panorama, tessuto, "e importante notare", "in un mondo in cui") e niente elenchi puntati superflui. Frasi di lunghezza varia con qualche frase corta, un'idea per frase, il caveat prende la sua frase. Non scrivere il numero due volte nella stessa frase. Niente raccordi da bot ("Torniamo a...", "Messe una accanto all'altra"). Nessun nome di persona. Tipografia: le regole di `content/STYLE.md` sono vincolanti (niente em-dash, en-dash, punto e virgola, puntini). Controllo: `grep -nP "[—–;…]" <file>` deve essere vuoto. Prosa del blog entro mille parole (tabelle e fonti escluse, come `REVIEW.md`).

## 5. Grafici e immagini: obbligatori
Ogni articolo ha almeno una figura nostra che regge la tesi, fatta con i dati del sito (fonte, anno, unita nella figura. Titolo che dice la notizia), e una copertina che e una foto reale con licenza libera compatibile con l'uso commerciale (Wikimedia Commons con `photo.py`, credito nel campo `cover_credit`, standard degli articoli recenti), pertinente al tema, senza persone riconoscibili in primo piano e mai generata con IA. Il grafico che avrebbe fatto da copertina resta come prima figura nel testo. SVG da `scripts.trend_articles.figures` (forme `bars`, `lines`, `scatter`, `extremes`) oppure, se nessuna forma regge la tesi, da uno script dedicato `scripts/trend_articles/figure_<tema>.py` come nei due pilota, classi CSS sui token (nessun colore cotto. `is-on` per l'evidenza), `<title>` e `<desc>` con i valori estremi, `cover_alt` descrittivo. Verifica con Playwright a 375 e 768 px, tema chiaro e scuro, senza scroll orizzontale, testo minimo 11 px, dimensioni dichiarate (CLS). Le figure vivono in `content/figures/<slug>/`, i marcatori `<!-- figura: nome -->` stanno su righe loro. La foto si sceglie guardando le anteprime (la pertinenza la decide un occhio) e si scrive nel rapporto la pagina della foto e la licenza. Per ogni immagine scrivi il modello usato e l'alternativa se la quota manca (figura da script: nessun modello. Foto: nessuno, la sceglie il leader).

Per i pezzi nati dal trend c'e anche `bin/py -m scripts.trend_articles.verify <file>` (frontmatter, foto, cifre del dossier, link). Sui pilota senza trend segnala errori noti di foto, dossier e trend: non e un cancello, il revisore ricalcola i numeri.

## 6. Rilievi, giri, approvazione
I rilievi vanno allo scrittore uno per uno e il leader verifica che siano tutti chiusi nel diff, non sulla parola. Massimo due giri di review (regola della direzione del 4/10, piu stretta dei tre di PIANO.md del 28/09): se dopo il secondo resta un bloccante lo decide la direzione. Il pezzo resta `draft: true` e va in una PR draft: la pubblicazione e del titolare, mai del leader. Il frontmatter non porta `author` (la firma la da `config/identita.yaml`). Nessun nome di persona nei testi.

## 7. Schede indicatore
Stessa pipeline sul testo (`content/indicators/<codice>.md`), con il contratto in `docs/INDICATOR_PAGES.md`, la guardia `bin/py -m scripts.editoriale.guardia <codice> --dossier ... --fonti ...` e lo stato in `app/editorial_state.py`. Priorita per impressioni: poche schede fanno quasi tutto il traffico, scrivi prima quelle.

## Cosa non si usa
Le skill a scheletro fisso dell'editorial-engine (in quarantena): lo schema fisso a sezioni e il primo tell di un testo da bot, e per le schede il contratto sta nei documenti del repo.
