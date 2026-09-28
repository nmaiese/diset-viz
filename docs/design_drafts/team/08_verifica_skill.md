# Verifica avversaria delle skill di ruolo

Fatta il 28 settembre 2026 con un workflow Claude, perche' e' un controllo sul lavoro del team leader e non un passaggio del team: tre verificatori indipendenti con tre lenti (coerenza con codice e runbook, copertura delle richieste di Nello, errori del vecchio Agent Team), poi una sintesi che ha riaperto ogni prova. 50 rilievi, 26 tenuti, 11 scartati come gusto o non provati. Tutti i 26 sono stati applicati alle skill, al runbook `04`, a `PIANO.md` e alla issue #287, salvo il 14, che tocca le skill utente di dev-tools e aspetta l'ok di Nello.

## 1. tutte, bloccante

**Problema.** Nessuna skill punta l'interprete. Il worktree dell'indicatore nasce con --setup skip e senza .venv, DIVARIO_PYTHON non sta in nessun profilo di shell e il runbook la esporta solo nella shell del leader. Al primo `bin/py` il worker riceve 127: lo scout, per la sua stessa regola ('Se il comando fallisce, ti fermi'), si ferma senza dossier e ferma la catena, lo scrittore non verifica lo store, il revisore non lancia la guardia. Un `export` fatto una volta non basta: in Claude Code lo stato della shell non resta fra un comando e l'altro, quindi serve il prefisso su ogni chiamata.

**Prova.** Riprodotto in questo worktree: `ls .venv` risponde No such file or directory, `env -u DIVARIO_PYTHON -u VIRTUAL_ENV bin/py -c 1` stampa 'bin/py: nessun interprete con le dipendenze del progetto.' con rc=127. grep di DIVARIO_PYTHON in ~/.zshrc, ~/.zshenv, ~/.profile, ~/.zprofile, ~/.bashrc: nessuna occorrenza. grep -c DIVARIO_PYTHON sulle quattro SKILL.md: 0. 04_orca_github.md:132-135 (export nella shell del leader, worktree con --setup skip). docs/WORKFLOW_ORCA.md:113-125 descrive proprio questo guasto. Con DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python, `bin/py -c 'import app'` risolve dentro questo worktree.

**Correzione.** In testa a ogni skill, subito dopo il titolo:

## Prima di tutto, l'interprete

Il worktree non ha una `.venv` sua, e una variabile esportata non resta fra un comando e l'altro. Ogni comando `bin/py` si lancia con il prefisso, a cominciare da questo:

```bash
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -c "print(__import__('app').__file__)"
```

Il percorso stampato deve stare dentro il tuo worktree. Se `bin/py` esce con 127 manca il prefisso, non è un guasto del progetto.

## 2. tutte, bloccante

**Problema.** Le skill stanno in `skills/editorial-team/<ruolo>/SKILL.md`, una cartella che né Claude né Codex caricano da soli. Il runbook promette che ogni --spec comincia con 'Leggi skills/editorial-team/<ruolo>/SKILL.md', ma nessuna spec lo fa. Così come è scritto il flusso, nessun worker legge la propria skill e tutto il loro contenuto resta senza effetto. La correzione sta nel runbook, non nelle skill.

**Prova.** 04_orca_github.md:535-537 ('Ogni `--spec` di questo runbook comincia con Leggi ...'). `grep -n Leggi` su 04 trova solo la riga 536. Le spec alle righe 166, 190, 206, 279 e 345 cominciano tutte con 'Target:'. Directory caricate: ~/.claude/skills, ~/.codex/skills, ~/.agents/skills (04:515-523). Nel repo non esistono né skills/ né .claude/skills/ (`ls .claude` mostra hooks, rules, settings.json).

**Correzione.** Nel runbook, in testa a ciascuna --spec delle sezioni 5, 6, 7 e 9: "Leggi skills/editorial-team/<ruolo>/SKILL.md e seguila. Questa spec la precisa: dove le due dicono cose diverse vale la spec, e lo scrivi nel worker_done." In testa a quella della sezione 10: "Leggi skills/editorial-team/scrittore/SKILL.md, la parte 'In una riparazione'."

## 3. scrittore, bloccante

**Problema.** Nessun passo del flusso crea `lavoro/<chiave>/brief.md`. Il leader pubblica sulla issue solo la riga e la fotografia, e la spec dello scrittore gli indica la issue. Il primo input dello scrittore non esiste, e con lui mancano dimensioni, perché, attualità e il nome del modello di content/esempi/ ('quello che il brief indica'). Senza brief, lo scrittore ripiega sul dossier, che il piano gli toglie apposta (frasi fatte, cifre di servizio, numeri non arrotondati). Lo stesso file lo legge il revisore e lo allega a opencode. In più `fonti.md`, da cui secondo la stessa skill vengono le cause, non è nella lista 'Che cosa leggi'.

**Prova.** grep di brief.md su docs/design_drafts/team/, STATUS.md e docs/WORKFLOW_ORCA.md: una sola occorrenza, 07_documenti_da_aggiornare.md:144, come prodotto futuro. 04_orca_github.md:175-177 (il leader pubblica 'la riga di una frase più la fotografia iniziale sulla issue'), 04:190 (spec: 'riga di una frase e fotografia dalla issue'), 04:454-461 (nessun ruolo scrive brief.md). PIANO.md:149-171 (le sei parti del brief e che cosa lo scrittore non riceve) e :263. scrittore/SKILL.md:14-22 (lista senza fonti.md) contro :44. revisore/SKILL.md:33 e :61.

**Correzione.** Nel runbook, sezione 5, dopo il worker-release dello scout: "Il team leader scrive lavoro/ter-12/brief.md con le sei parti di PIANO.md 'Il brief dello scrittore' (che cosa misura in una riga, fotografia, dimensioni, perché, attualità, il file di content/esempi/ da usare come modello) e ne pubblica una copia sulla issue." La sezione 8 lo committa già con lavoro/ter-12/. Nella spec 04:190, 'riga di una frase e fotografia dalla issue' diventa 'il brief in lavoro/ter-12/brief.md'. Nella skill dello scrittore, sotto il punto 1: "Se brief.md non c'è, non scrivi e mandi un'escalation al team leader. dossier.json e scout_web.md non li apri: le cifre che ti servono sono nel brief." E un punto in più nella lista: "`lavoro/<chiave>/fonti.md`, per le cause, le citazioni e gli URL da linkare."

## 4. revisore, importante

**Problema.** La skill fa scrivere lo stato in un commento della issue. Il runbook lo tiene nel corpo della issue e spiega perché: tutti gli agenti hanno l'identità di Nello, e `gh issue comment --edit-last` riscriverebbe l'ultimo commento di chiunque, per esempio il brief del leader. Contraddice anche la spec che il revisore riceve. La skill non dice nemmeno da dove prendere il numero della issue, che la spec non contiene. La skill ha copiato PIANO.md:244, che dice ancora 'un solo commento Stato modificato sul posto' ed è smentito dal runbook.

**Prova.** 04_orca_github.md:380-395 ('è la sezione `## Stato` in fondo al corpo della issue ... non un commento ... `gh issue comment --edit-last` modificherebbe l'ultimo commento di chiunque'). 04:279, spec del revisore: 'Aggiorna la sezione Stato nel corpo della issue (gh issue view --json body, poi gh issue edit --body-file)', senza $ISSUE. PIANO.md:244-245. revisore/SKILL.md:82-83.

**Correzione.** Sostituire con: "Poi aggiorni la sezione `## Stato` nel corpo della issue, mai con un commento e mai con `gh issue comment --edit-last`. Il numero della issue lo prendi da `Closes #n` nel corpo della PR. `gh issue view <issue> --json body --jq .body > /tmp/stato-<issue>-<iterazione>.md`, sostituisci il blocco da `## Stato` alla fine (Fase, SHA, Prossimo passo, Chi lo fa), poi `gh issue edit <issue> --body-file /tmp/stato-<issue>-<iterazione>.md`. Il file sta in /tmp e non nel worktree, che deve restare pulito." In PIANO.md:244-245, 'C'è un solo commento Stato modificato sul posto' diventa 'Lo stato è la sezione ## Stato nel corpo della issue, riscritta sul posto'.

## 5. revisore, importante

**Problema.** La spec del revisore non contiene nessun comando della guardia, quindi il revisore lo salta o se lo inventa. Se lo inventa senza `--dossier`, la guardia salta proprio il controllo delle cifre, l'unico che le confronta con il dossier. E nella sezione 8 il leader lancia solo `git diff --check` e la suite, non lo script con il dossier: il giro del revisore è l'unico controllo garantito delle cifre.

**Prova.** 04_orca_github.md:279, la spec del revisore non nomina la guardia. 04:220-224 (il leader lancia diff --check e unittest). Issue #287: `bin/py -m scripts.editoriale.guardia <chiave> [--dossier lavoro/<chiave>/dossier.json]` e 'Cifre contro il dossier, solo quando il dossier c'è'. revisore/SKILL.md:27-29.

**Correzione.** Sostituire con: "Lanci la guardia con il dossier: `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia <chiave> --dossier lavoro/<chiave>/dossier.json`. Un codice d'uscita diverso da zero vuol dire guardia rossa." Lo stesso comando va aggiunto nella --spec di 04:279.

## 6. revisore, importante

**Problema.** La skill confronta gli SHA solo all'inizio e poi pubblica senza ricontrollarli. Il runbook e il piano chiedono il confronto subito prima di pubblicare (rilievo 6): fra guardia, lettura e opencode, che può durare fino a 600 secondi, un push può arrivare. La skill chiede poi un'escalation, mentre il runbook vuole che il revisore non pubblichi e lo dica nel worker_done.

**Prova.** 04_orca_github.md:311-321 ('Nel proprio worktree il revisore verifica prima di pubblicare ... il revisore non pubblica e lo dice nel suo worker_done'). 04:279 ('Prima di pubblicare confronta git rev-parse HEAD ... se sono diversi non pubblicare'). PIANO.md:204-205. revisore/SKILL.md:70-79, la sezione 'Il verdetto' pubblica senza un nuovo controllo.

**Correzione.** Nella sezione 'Il verdetto', subito prima di `gh pr review`: "Rilanci `git rev-parse HEAD` e `gh pr view <n> --json headRefOid -q .headRefOid`. Se non coincidono fra loro e con lo SHA della spec, non pubblichi niente e lo scrivi nel `worker_done` con i due SHA." Nella sezione iniziale, 'Mandi un'escalation al team leader.' diventa 'Non pubblichi e lo scrivi nel `worker_done` con i due SHA.'

## 7. grafico, importante

**Problema.** Nei modelli della skill `evidenzia` e `regione` sono senza virgolette. `parse_args` legge un valore nudo fino al primo spazio, e tre regioni hanno uno spazio nel nome. Con `evidenzia` salta tutta l'evidenza, anche delle regioni scritte bene dopo. Con `regione` il ritratto sparisce. In più i nomi devono essere quelli dei dati, non quelli ufficiali: 'Trentino-Alto Adige' con il trattino si perde. In nessun caso c'è un errore.

**Prova.** app/charts.py:56, `_ARG_RE = r'(\w+)\s*=\s*(?:"([^"]*)"|([^\s"]+))'`. Riprodotto qui con bin/py: `parse_args('con=ter-901 evidenzia=Friuli-Venezia Giulia,Campania didascalia="x"')` dà evidenzia='Friuli-Venezia'. `parse_args("regione=Valle d'Aosta con=ter-12,ter-901 ...")` dà regione='Valle'. `charts.figure('ter-12', {'con':'ter-901','evidenzia':'Trentino-Alto Adige,Calabria'}, 'regione')` dà una figcaption con solo 'In evidenza: Calabria.'. Anche gli esempi di docs/INDICATOR_PAGES.md:343 e :354 sono senza virgolette.

**Correzione.** I due modelli con le virgolette:
`<!-- grafico: dispersione con=<codice> evidenzia="<Regione>,<Regione>" didascalia="<una frase>" -->`
`<!-- grafico: ritratto regione="<Regione>" con=<codice>,<codice>,<codice> didascalia="<una frase>" -->`
Sotto: "I nomi delle regioni si scrivono come nei dati, non nella forma ufficiale: `Trentino Alto Adige` senza trattino, `Friuli-Venezia Giulia`, `Valle d'Aosta`. La didascalia non contiene virgolette doppie né `>`. Un nome sbagliato sparisce senza errore: nella verifica controlli che la figcaption dica 'In evidenza:' con tutte le regioni che hai chiesto."

## 8. grafico, importante

**Problema.** La spec del grafico e il piano chiedono i colori delle ripartizioni e mai l'arancio, e il piano scrive che la figura non richiede codice. Il renderer invece dà a tutti i punti la stessa classe grigia e colora le regioni in `evidenzia`, che la skill raccomanda, con `--data-focus`, cioè l'arancio. Toccando solo il marcatore il criterio di accettazione non si può rispettare, e la skill non dice che cosa fare. A non seguire la regola è il renderer: CLAUDE.md vuole i punti dei grafici nel colore della ripartizione, e i token esistono ma charts.py non li usa. 'Mai l'arancio' è invece più stretto di CLAUDE.md, che ammette l'arancio per ciò che è in evidenza.

**Prova.** 04_orca_github.md:206 ('colori delle ripartizioni, mai l'arancio ... Constraints: solo il marcatore assegnato'). PIANO.md:221-224 ('non richiede codice') e :238. app/charts.py:145-148 (una sola classe `scatter__dot`, più `is-on`). app/static/css/ds/components.css:525-526 (`--cmp` e `--data-focus`). app/static/css/ds/system.css:65 (`--data-focus: #a75001`) e :81-83 (`--area-nord`, `--area-centro`, `--area-sud`, non usati da charts.py). site.css:1055 nel ripiego usa `--accent`. CLAUDE.md, Vincoli, identità visiva.

**Correzione.** In grafico/SKILL.md, sotto 'Che cosa puoi usare': "La dispersione di oggi non colora per ripartizione: i punti sono grigi (`--cmp`) e quelli in `evidenzia` prendono `--data-focus`, l'arancio. Se la spec chiede i colori delle ripartizioni, con un marcatore non si ottengono. Non tocchi `app/charts.py` né il CSS: lo scrivi nel `worker_done`, e il team leader decide se aprire prima una PR del renderer o togliere il criterio dalla spec." Nel runbook 04:206 e in PIANO.md:224 e :238, 'colori delle ripartizioni, mai l'arancio' diventa 'colori delle ripartizioni se il renderer li ha (oggi no: serve una PR di app/charts.py da unire prima), l'arancio solo per le regioni in evidenza'.

## 9. grafico, importante

**Problema.** La verifica della resa, l'unica prova che la skill chiede nel worker_done, parte da un eseguibile che nel worktree dell'indicatore non esiste. In più il loader degli articoli resta in cache per tutta la vita del processo, e se non riesce a leggere un file ripiega in silenzio sullo scheletro: un marcatore corretto dopo l'avvio non si vede, e un file rotto non dà errore in pagina. In primo piano, infine, gunicorn blocca il terminale del worker.

**Prova.** `ls .venv` in questo worktree: No such file or directory. `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m gunicorn --version` risponde 'gunicorn (version 23.0.0)'. app/indicator_texts.py:84-94 (`@functools.lru_cache(maxsize=1)` su `_load`, `load_all(strict=False)`, ripiego `{}` su StoreError). CLAUDE.md, Comandi ('Dopo aver cambiato i dati, riavvia gunicorn').

**Correzione.** "Avvii il sito in background con `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m gunicorn run:app -b 127.0.0.1:5050`, dopo l'ultima modifica ai marcatori, e lo riavvii dopo ognuna: gli articoli restano in cache per tutta la vita del processo. Prima controlli che `bin/py scripts/indicator_store.py --show <chiave>` esca con 0, perché un file illeggibile ricade sullo scheletro senza errore in pagina."

## 10. scrittore, importante

**Problema.** Le fonti esterne la pagina non le compone. 'Fonti dell'analisi' mostra il campo `fonti` del frontmatter più le fonti già nel registro del corpus, e le fonti nuove dello scout entrano nel registro solo dopo il merge. Seguendo la skill, lo scrittore cita Banca d'Italia o SVIMEZ nella prosa e lascia vuoto `fonti`: il lettore vede l'attribuzione e non trova la fonte, che è il difetto ter-176 descritto nel codice. La skill tace anche sul lead, il paragrafo prima della prima sezione, che è anche la meta description.

**Prova.** app/templates/v1/indicatore.html:373 (`page_article.fonti`). app/indicator_texts.py:223-237 (`visible_sources`, 'authored = ... entry.get("fonti")', docstring sul caso ter-176) e :388 ("fonti": visible_sources(entry)). scout/SKILL.md:62-63 (le fonti nuove le promuove il leader dopo il merge). content/indicators/901.md:3-7 (fonti con testo e url). content/indicators/12.md (frontmatter con solo key, level, vintage, poi il lead). docs/INDICATOR_PAGES.md:222. .claude/rules/editorial.md:34-37.

**Correzione.** Sostituire con: "Il blocco 'Come leggere il dato' e il cruscotto li compone la pagina, e non li riscrivi. Le fonti esterne no: ogni URL di `fonti.md` che citi nella prosa va anche nel frontmatter `fonti:`, con `testo` (istituzione, titolo, data) e `url`, come in `content/indicators/901.md`, altrimenti in 'Fonti dell'analisi' non compare. Prima della prima sezione scrivi il lead, una o due frasi, che è anche la description in SERP."

## 11. grafico, importante

**Problema.** Il grafico non può toccare il testo, lo scrittore scrive prima e la sua skill non parla mai di figure, e fra grafico e PR nessun passo rilancia lo scrittore. Il paragrafo che nomina la figura quindi di solito non c'è, la domanda 5 del revisore risponde no, e si consuma uno dei tre giri su un requisito che nessun ruolo poteva soddisfare. La richiesta contraddice anche il contratto delle figure: il pezzo va scritto perché regga senza, dato che una figura che non si disegna sparisce, e un paragrafo che nomina una figura assente resta monco.

**Prova.** grafico/SKILL.md:42-44 e :56-58. grep di 'grafic|figura|marcatore' su scrittore/SKILL.md: solo 'tipografici', riga 54. 04_orca_github.md:199-213 (grafico) passa direttamente alla sezione 8 (guardia e PR). revisore/SKILL.md:47. PIANO.md:122 (scrittore: 1 più 2 riparazioni). docs/INDICATOR_PAGES.md, 'Le figure dentro l'articolo' ('Il pezzo va scritto perche' regga anche senza').

**Correzione.** In grafico/SKILL.md, passo 2: "Il marcatore va subito dopo il paragrafo che fa l'affermazione che la figura mostra: è quel paragrafo a richiamarla. Se nessun paragrafo la fa, la figura non si mette." Al posto di 'lo scrivi nel `worker_done` e lo fa lo scrittore': "lo scrivi nel `worker_done` parola per parola, e il team leader lancia la riparazione dello scrittore prima del commit, non dopo la review." In scrittore/SKILL.md, 'La sostanza': "Dove il perché passa da un'altra grandezza (per ter-12 il PIL pro capite, ter-901), il confronto lo scrivi in parole, in un paragrafo suo, perché regga anche senza figura: il grafico metterà lì sotto la dispersione." Nel runbook, fra sezione 7 e 8: "Se il worker_done del grafico chiede una frase, parte una riparazione dello scrittore prima del commit."

## 12. revisore, importante

**Problema.** La guardia di #287 pretende che ogni numero del testo corrisponda a una cifra del dossier. Le previsioni 2026 e il dato recente fuori catalogo, che scout e scrittore devono usare, stanno invece in fonti.md. La spec dello scrittore accetta già 'ogni cifra riconducibile al dossier o a fonti.md'. Un articolo che fa quello che chiede il piano esce rosso, la skill trasforma il rosso in DA CORREGGERE automatico, e la riparazione toglie proprio quelle cifre.

**Prova.** Issue #287, controllo 1 ('ogni numero del testo deve corrispondere a una cifra del dossier'). 04_orca_github.md:190 (acceptance: 'ogni cifra riconducibile al dossier o a fonti.md'). scout/SKILL.md:23-24 e :30-32. scrittore/SKILL.md:49-50. PIANO.md:162.

**Correzione.** In revisore/SKILL.md, dopo la frase citata: "Fa eccezione una cifra che sta, identica, nella citazione letterale di una riga di `fonti.md` e che la frase attribuisce a quell'istituzione: non è un rilievo, e la segnali nel commento per Nello." Nella spec di #287, controllo 1: "a una cifra del dossier o a una cifra della colonna 'citazione letterale' di lavoro/<chiave>/fonti.md".

## 13. revisore, importante

**Problema.** La skill prevede solo l'uscita con 0 e output vuoto. Un allegato che non esiste, oggi brief.md (vedi il rilievo sul brief), fa uscire opencode con 1 e 'File not found' prima di chiamare il modello. Il revisore non sa se è un guasto da ripiego o un parere vuoto, e il secondo parere fisso della decisione 8 salta.

**Prova.** Riprodotto qui: `timeout 60 opencode run "Rispondi solo OK" -m ollama-cloud/gpt-oss:120b -f lavoro/ter-12/brief.md < /dev/null` stampa 'Error: File not found: lavoro/ter-12/brief.md' con rc=1. Il worktree del revisore nasce da origin/$PR_BRANCH (04_orca_github.md:284-286) e ha solo i file committati. revisore/SKILL.md:56-66.

**Correzione.** Prima del blocco: "Controlli che i due allegati esistano (`test -f`)." Al posto della frase citata: "Se opencode esce con un codice diverso da 0, o con l'output vuoto, il parere non c'è."

## 14. tutte, importante

**Problema.** Due skill utente restano attive per Claude e per Codex, con trigger che coincidono col compito dello scrittore e del revisore, e riportano il sistema vecchio. italian-product-copywriter si attiva su 'full articles, data-journalism posts ... DISET' e porta uno 'Article Skeleton' di default (definire la metrica, risultato con i numeri, che cosa guida la differenza, limiti e caveat), una claim table per ogni cifra e un 'Agent Pre-Publish Contract' con un caveat obbligatorio. italian-data-sources impone di citare SEMPRE una fonte aggiuntiva e di mettere tutte le fonti in una sezione finale '## Fonti', che la pagina compone già. Nessuna skill di ruolo dice di ignorarle, e la quarantena del 28 settembre ha preso solo le altre due.

**Prova.** ls ~/.claude/skills: italian-product-copywriter, italian-data-sources, seo-content-strategy (link a dev-tools/claude/skills). ls ~/.codex/skills: italian-product-copywriter, italian-data-sources. ls ~/.codex/skills-quarantena: solo editorial-pipeline e italian-editorial-quality-gate. italian-product-copywriter/SKILL.md:3. references/article-writing-playbook.md:20 ('Article Skeleton'), :51 ('Evidence And Claim Table'), :67 ('Agent Pre-Publish Contract'). italian-data-sources/SKILL.md:31-35 ('Regola DISET'). 04_orca_github.md:540-544 motiva la quarantena con lo stesso profilo di attivazione.

**Correzione.** In ogni skill di ruolo, subito dopo il titolo: "Questa skill è l'unico contratto del ruolo. Non carichi italian-product-copywriter, italian-data-sources né seo-content-strategy, e non applichi il loro schema di articolo, la claim table, il caveat obbligatorio o la sezione finale '## Fonti'." Per il pilota, con l'ok di Nello perché tocca dev-tools, mettere in quarantena anche italian-product-copywriter (~/.codex/skills e il link in ~/.claude/skills).

## 15. scrittore, importante

**Problema.** La skill manda lo scrittore a due documenti che, letti per intero come chiede CLAUDE.md ('leggi il documento, non agire sul riassunto'), gli riportano la forma vecchia. STYLE.md dice di sé che le pagine indicatore non si scrivono da lì e che per loro vale solo 'Tecniche da giornalista'. docs/INDICATOR_PAGES.md, di cui la skill cita solo 'La forma libera', porta 'L'articolo: quattro ruoli' e 'Confronto con l'ultimo anno', con 'Dichiarare quanti territori compongono la base comune', 'Indicare quante regioni aumentano, diminuiscono o restano stabili' e 'Non attribuire cause a una variazione osservata': le frasi a inventario della bozza carceri, più un divieto che contraddice 'soprattutto perché'. .claude/rules/editorial.md, che Claude carica da solo su content/**, dice 'un lead più quattro sezioni ordinate'. Il piano corregge questi documenti solo nella fase 5, dopo il pilota.

**Prova.** content/STYLE.md:7-13. docs/INDICATOR_PAGES.md:211-219 e :419-441. .claude/rules/editorial.md:2-3 (paths content/**) e :27-29. CLAUDE.md, 'Se un argomento qui sotto ha un documento, leggi il documento'. scrittore/SKILL.md:20 e :27-28. PIANO.md:390-399 (Fase 5, INDICATOR_PAGES e editorial.md riga 28 dopo il pilota). 03_diagnosi_qualita.md:144-192 (le frasi della bozza carceri).

**Correzione.** Il punto 3 diventa: "3. Di `content/STYLE.md` le 'Regole tipografiche (vincolanti)' e le 'Tecniche da giornalista (fai così)', niente altro: il resto vale per il blog." Al posto di 'Lo schema del file è in `docs/INDICATOR_PAGES.md`, "La forma libera".': "Di `docs/INDICATOR_PAGES.md` leggi solo 'La forma libera' e 'Le figure dentro l'articolo'. 'L'articolo: quattro ruoli', 'Risposte obbligatorie', 'Confronto con l'ultimo anno' e 'Trend di lungo periodo' descrivono la pagina composta e il cruscotto, non il tuo pezzo, e la regola che parla di quattro sezioni ordinate non vale per la forma libera. 'Non attribuire cause' vuol dire non dedurne una da solo: la causa che un'istituzione di `fonti.md` dà, con il suo nome, la riporti."

## 16. revisore, importante

**Problema.** Nello chiede un revisore della correttezza e della scrittura e uno scrittore dall'italiano impeccabile, ma nessuna delle cinque domande controlla l'italiano: grammatica, concordanze, accenti, refusi, frasi che reggono due idee. La guardia guarda solo i quattro caratteri vietati, e il secondo parere risponde alle stesse domande 1-3. Un pezzo con un errore di concordanza, come quello trovato nella bozza carceri, passa ogni controllo.

**Prova.** PIANO.md:24-26. revisore/SKILL.md:36-47. Issue #287, controllo 5 (solo em-dash, en-dash, punto e virgola, puntini). 03_diagnosi_qualita.md:170-175 ('Errore di italiano ... È il tipo di errore che nessun gate vede').

**Correzione.** "3. Si legge come prosa discorsiva, in italiano corretto? Nessun errore di grammatica, concordanza, accento o refuso, nessuna frase che regge due idee. Non è un elenco travestito né una classifica letta ad alta voce, i titoli sono affermazioni e non etichette, e non c'è una sezione di cautele generiche." Restano cinque domande, e il secondo parere riceve la 3 così.

## 17. revisore, importante

**Problema.** La descrizione di che cosa conta l'indicatore non la controlla nessuno: né il dossier né fonti.md portano la definizione della fonte, e la guardia non la guarda. È la classe di errore trovata in 4 articoli su 11, e lo strumento deterministico esiste. Il revisore è Codex e non carica .claude/rules/, dove lo strumento è citato.

**Prova.** .claude/rules/editorial.md:46-60 ('rileggere undici articoli contro i dati ha trovato zero errori aritmetici e quattro descrizioni sbagliate'). Lanciato qui: `bin/py scripts/definition_check.py --show ter-12` risponde 'fonte: Persone in cerca di occupazione in età 15 anni e oltre sulle forze di lavoro nella corrispondente classe di età (%) (media annua)' e 'nessun rilievo'. Nessuna delle quattro skill nomina definition_check. 04_orca_github.md:290 (revisore Codex).

**Correzione.** Nella domanda 4 aggiungere: "La descrizione di che cosa conta l'indicatore torna con la definizione della fonte (`bin/py scripts/definition_check.py --show <chiave>`)? Un suo rilievo è un posto dove guardare, non un verdetto." In scrittore/SKILL.md, 'Che cosa leggi', un punto in più: "`bin/py scripts/definition_check.py --show <chiave>`, che cosa conta l'indicatore per la fonte, prima di spiegare che cosa misura."

## 18. scrittore, importante

**Problema.** Le due frasi date come modello diventano un'avvertenza fissa: lo scout segna 'non trovato' dove non trova, e ogni 'non trovato' diventa la stessa frase su tutte le schede, cioè la voce ripetuta che docs/AUDIT_VOCE.md misura. Manca la strada che la diagnosi aveva validato: spiegare come si muove il numero (che cosa sta sopra e sotto la frazione, che cosa conta la definizione), che non è una causa e non chiede una fonte. La domanda 2 del revisore ('Una causa senza fonte è un no'), senza questa eccezione, spinge a togliere anche la meccanica. Il ter-12 di oggi regge il suo limite proprio sul denominatore.

**Prova.** scrittore/SKILL.md:44-46. scout/SKILL.md:55-57. revisore/SKILL.md:39-40. 03_diagnosi_qualita.md:180-184 ('Questa non è una causa inventata, è la meccanica del rapporto, e sta nella definizione') e :521 ('S3. Il perché ha una fonte, o è la meccanica del rapporto'). content/indicators/12.md:27 ('chi rinuncia a cercare sparisce dal denominatore').

**Correzione.** Scrittore: "Le cause vengono solo da `fonti.md`, con l'istituzione nominata nella frase e il link. Come si muove il numero (che cosa sta sopra e che cosa sta sotto la frazione, che cosa conta la definizione) non è una causa, e lo spieghi tu. Dove il brief dice 'non spiegato' e la meccanica non basta, lo dici una volta, con parole tue, dove il lettore se lo chiede. Non inventi mai una causa." Revisore, domanda 2, dopo 'Una causa senza fonte è un no': "La meccanica del rapporto e la definizione non sono cause."

## 19. scout, importante

**Problema.** Il comando è in primo piano, quindi non gira 'mentre cerchi tu' e blocca lo scout. Con `timeout 900` supera anche il tetto dello strumento Bash di Claude Code, e lo scout è Claude: senza un timeout esplicito il comando viene troncato a 120 secondi, al massimo a 600. Il giro web fisso della decisione 8 salta quasi sempre. In più all'inizio del turno la cartella `lavoro/<chiave>/` non esiste, e il redirect fallisce prima ancora che agy parta.

**Prova.** scout/SKILL.md:41-45. 04_orca_github.md:170 (scout `--agent claude --model sonnet`). Descrizione dello strumento Bash di Claude Code: 'timeout ... default 120000, max 600000', `run_in_background` per i comandi lunghi. `ls lavoro` in questo worktree: No such file or directory.

**Correzione.** Prima del blocco: `mkdir -p lavoro/<chiave>`. Dopo il blocco: "Lo lanci in background (in Claude Code con `run_in_background`, altrimenti chiudendo la riga con `&`), e prima del `worker_done` aspetti che finisca. Se `scout_web.md` è vuoto, il giro non c'è stato e lo scrivi."

## 20. scout, importante

**Problema.** `gemini-3.6-flash` non è un id valido per agy, che vuole il suffisso dello sforzo. Il ripiego fallisce subito e lo scout resta senza giro web proprio quando il primario non risponde. Lo stesso id sbagliato sta nel runbook e nel piano.

**Prova.** `agy models` lanciato qui elenca gemini-3.6-flash-high, gemini-3.6-flash-medium, gemini-3.6-flash-low e gemini-3.1-pro-high, nessun gemini-3.6-flash senza suffisso. Il verificatore di coerenza ha avuto rc=1 con '--model gemini-3.6-flash requires --effort (available: low, medium, high)', e rc=0 con gemini-3.6-flash-high. 04_orca_github.md:180, PIANO.md:105.

**Correzione.** "Se fallisce, riprovi una volta con `--model gemini-3.6-flash-high` e poi vai avanti senza." Stessa correzione in 04_orca_github.md:180 e PIANO.md:105.

## 21. revisore, minore

**Problema.** Due difetti nella stessa riga. La domanda 4 chiede se ogni affermazione torna con il dossier, ma dossier.json, l'unico file con tutte le dimensioni e le loro distanze, non è fra le letture. E il revisore apre brief e fonti prima dell'articolo: quando risponde alla domanda 1 conosce già la riga del brief, quindi la lettura da lettore promessa in apertura della skill non avviene. La diagnosi voleva un primo passaggio sul solo testo.

**Prova.** revisore/SKILL.md:8-9 ('come lo leggerà una persona ... e poi come lo leggerebbe un redattore') contro :33-34, e :44-46 (domanda 4 sul dossier). 03_diagnosi_qualita.md:416-418 ('Nel primo legge solo il testo, senza dossier né brief'). Il dossier è committato con lavoro/ter-12/ (04_orca_github.md:226).

**Correzione.** "Prima leggi solo l'articolo, come un lettore, e rispondi alle domande 1 e 3. Poi apri `lavoro/<chiave>/dossier.json` (in particolare le dimensioni), `lavoro/<chiave>/brief.md` e `lavoro/<chiave>/fonti.md` per le domande 2, 4 e 5." Gli allegati di opencode restano quelli di PIANO.md:107.

## 22. scout, minore

**Problema.** La tabella dei permessi del runbook concede allo scout solo dossier.json e fonti.md, e la skill fa scrivere anche scout_web.md e scout_web.err. `lavoro/` non è in .gitignore, e il `git add lavoro/ter-12/` della sezione 8 porta nella PR di contenuto, e poi su master, l'output grezzo di agy, fatto di piste non verificate, e il suo stderr.

**Prova.** 04_orca_github.md:456 (scout: dossier.json, fonti.md). 04:226 (`git add content/indicators/12.md lavoro/ter-12/`). `git check-ignore -v lavoro/ter-12/fonti.md`: nessun risultato, rc=1. scout/SKILL.md:44 (`2> lavoro/<chiave>/scout_web.err`).

**Correzione.** Nella skill, lo stderr in /tmp: `2> /tmp/scout_web-<chiave>.err`. Nel runbook, 04:456, aggiungere `lavoro/<chiave>/scout_web.md` alla riga dello scout, e in 04:226 elencare i file: `git add content/indicators/12.md lavoro/ter-12/dossier.json lavoro/ter-12/fonti.md lavoro/ter-12/brief.md`.

## 23. scrittore, minore

**Problema.** `<chiave>` vale `ter-12` nei percorsi `lavoro/` e in `--show`, ma `filename_for` vuole la chiave interna. Chiamata con la stessa chiave dà `ter-12.md`, non `12.md`. Lo store poi rifiuta il file, ma la skill indica la funzione senza dire con quale argomento.

**Prova.** Riprodotto qui con bin/py: `filename_for('ter-12')` restituisce 'ter-12.md', `filename_for('12')` restituisce '12.md'. I percorsi di lavoro usano il codice dell'URL (04_orca_github.md:226, `lavoro/ter-12/`).

**Correzione.** "il nome lo dà `scripts/indicator_store.filename_for` sulla chiave interna (`12`, `bes:06POL012P`), non sul codice dell'URL (`ter-12`)"

## 24. scrittore, minore

**Problema.** Presa alla lettera, la regola vieta la scala umana che 'Tecniche da giornalista', l'unica parte di STYLE.md che vale per le schede, chiede espressamente ('una donna su tre', 'tre volte la media'). Lo scrittore riceve due istruzioni che si contraddicono. L'arrotondamento invece resta giustamente al brief.

**Prova.** content/STYLE.md:12-13 (Tecniche da giornalista vale anche per le schede) e :99-101 ('Trasforma un numero in una scala umana'). 03_diagnosi_qualita.md:398-400 ('Arrotondare è una trasformazione, e le trasformazioni le fa il dossier').

**Correzione.** "**Le cifre sono solo quelle del brief**, scritte come sono scritte lì. Puoi dirle in scala umana ('una persona su dieci') se il valore resta quello, mai con un numero nuovo."

## 25. revisore, minore

**Problema.** Incoerenza interna: per la riga sopra ogni 'no' porta a DA CORREGGERE, ma qui compaiono 'i soli rilievi bloccanti', che la skill non definisce mai. Il revisore deve inventarsi una scala che il piano non ha, e i rilievi non bloccanti non si sa dove vadano.

**Prova.** revisore/SKILL.md:72-73. PIANO.md:199 ('Per ogni no il revisore dà la frase citata, il motivo e la correzione minima'), nessuna gravità.

**Correzione.** "- `DA CORREGGERE` altrimenti, con un rilievo per ogni 'no' in una lista."

## 26. revisore, minore

**Problema.** REVIEW.md dice che ogni PR riceve i suoi passaggi, e il passaggio 2 porta 'Il filo': il corpo della PR con la scaletta e le righe `porta` del `redattore`, che nel flusso nuovo non esistono. La skill non dice se per le PR run:team vale ancora. Che il revisore Codex apra REVIEW.md è probabile, non verificato: CLAUDE.md e AGENTS.md non lo nominano, il template della PR sì.

**Prova.** REVIEW.md:3-7 e :34-39. .github/PULL_REQUEST_TEMPLATE.md ('La review segue REVIEW.md'). grep di REVIEW in CLAUDE.md e AGENTS.md: vuoto.

**Correzione.** Nella skill del revisore: "Per le PR run:team il contratto di review è questo. Di REVIEW.md 'Il filo' non si applica, perché la PR non porta una scaletta. Il passaggio 3, igiene e sicurezza, resta."

## Scartati

- "manca (scout, 'I numeri collegati': ter-15, ter-16, ter-17, ter-408, ter-108, bes-03LAV002-N22)": Allarga lo scopo del piano approvato. PIANO.md:158-159 fissa le dimensioni di ter-12 (il genere, ter-175 e ter-176), la frase 'tutti i numeri che abbiamo sul tema' non sta nei documenti del team (grep vuoto), e il fix cambia anche la guardia di #287. È una decisione di progetto per Nello, non un difetto della skill.
- "| voce | istituzione | data di pubblicazione | URL | citazione letterale | limite d'uso |": Colonne e voci di fonti.md sono il contratto approvato (PIANO.md:132-144, spec 04:166). Aggiungere la colonna 'che cosa spiega', la domanda del leader e un tetto di righe è una scelta di disegno, non un difetto.
- "4. Ogni affermazione torna con il dossier e con `fonti.md`? (proposta di limitarla a cause e attribuzioni)": La domanda è quella approvata (PIANO.md:195) e copre affermazioni che la guardia non controlla, come conteggi e insiemi ('in tutte e venti le regioni'), che REVIEW.md:20-23 affida a una verifica umana. 'Non fai mappe di paragrafi o di cifre' non la contraddice.
- "La lettura non serve finché le cifre non tornano.": Nella sezione 8 (04:220-224) il leader lancia solo diff --check e la suite, non la guardia con --dossier, quindi il giro del revisore è l'unico controllo garantito delle cifre contro il dossier. Il difetto vero, il comando mancante, è tenuto.
- "Il testo di oggi della scheda (`bin/py scripts/indicator_store.py --show <chiave>`),": Scelta dichiarata e limitata ('solo per sapere che cosa non ripetere'). La diagnosi 03:262-269 parla del modello di registro, non di sapere che cosa c'era prima.
- "Deve uscire sapendo che cosa misura, com'è": Ricalca la richiesta di Nello (PIANO.md:24-25) ed è un obiettivo per il lettore, non una scaletta: la skill subito dopo dice che la forma la decide lo scrittore. È gusto.
- "**Un solo** modello di registro da `content/esempi/`, quello che il brief": Il brief nomina il file e la skill dice di leggere quello. Il README della cartella è una lettura non richiesta, e porta anche avvertenze utili (non citare le cifre degli estratti, non copiarne i caratteri). Rischio non dimostrato.
- "- `PRONTA PER NELLO` se la guardia è verde e le cinque risposte sono sì. (proposta di una scala di gravità)": La nuova scala renderebbe consultive le domande sulla prosa, che sono il motivo del pilota (il testo 'molto grezzo' di PIANO.md:13-15), e il piano non la prevede. Resta tenuta solo l'incoerenza interna dei 'soli rilievi bloccanti'.
- "-m ollama-cloud/gpt-oss:120b -f <articolo> -f lavoro/<chiave>/brief.md < /dev/null (proposta di togliere il brief o aggi": Gli allegati sono fissati da PIANO.md:107 e dalla spec 04:279. Il difetto vero, il file che non esiste e l'uscita con 1 non gestita, è nei rilievi sul brief e su opencode.
- "Il marcatore va subito dopo il paragrafo che fa l'affermazione (parte sulla spec che fissa la figura prima dell'articolo": La spec del pilota applica a ter-12 il candidato di PIANO.md:221-224, la skill descrive il caso generale: non si contraddicono. La domanda 5 è approvata (PIANO.md:197) e resta com'è. Il difetto sul paragrafo che nomina la figura è tenuto.
- "fix di coerenza sui colori: 'colori del renderer: punti --cmp, regioni accese --data-focus'": Sancirebbe una violazione di CLAUDE.md, che vuole i punti dei grafici nel colore della ripartizione, con i token --area-* già in system.css:81-83. Il rilievo è tenuto con la correzione che passa la decisione al team leader.
