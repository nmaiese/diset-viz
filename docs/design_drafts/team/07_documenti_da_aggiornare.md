# I documenti da aggiornare, riga per riga

Inventario per il cantiere 1 di `PIANO.md` (sezione 5). Per ogni riga: che cosa
dice oggi, che cosa dovrà dire, e quando cambiarla. "Subito" vuol dire che la
riga è già falsa oggi, indipendente dal piano. "Dopo approvazione" vuol dire
che diventa falsa solo quando il team parte, e quindi si scrive insieme al
resto del cantiere 1, non prima.

## CLAUDE.md

- `CLAUDE.md:35` | oggi dice: "la pipeline automatica non è attiva" | dovrà
  dire: che le schede nuove passano dal team a quattro ruoli descritto in
  `docs/WORKFLOW_ORCA.md`, e che le circa 300 schede a quattro sezioni fisse
  restano finché il team non le riscrive | quando: dopo approvazione
- `CLAUDE.md:137-138` | oggi dice: "Non c'è una rubrica a punti e non c'è un
  lint della prosa" | dovrà dire: la stessa cosa resta vera per la lettura
  umana (il piano non introduce un punteggio), ma va aggiunta una riga sulla
  guardia deterministica del cantiere 3 e sui criteri passa/non passa del
  revisore, perché oggi il lettore capisce "nessun controllo automatico" e
  dopo il piano ce n'è uno bloccante | quando: dopo approvazione

## AGENTS.md

- `AGENTS.md:30-32` | oggi dice: "La vecchia pipeline editoriale esterna è
  dismessa e verrà riscritta da zero" | dovrà dire: che la riscrittura è in
  corso con un team di quattro ruoli interno al repository, non un repository
  esterno, e puntare a `docs/WORKFLOW_ORCA.md` per il dettaglio | quando: dopo
  approvazione

## README.md (radice)

- `README.md:102-104` | oggi dice: "La vecchia pipeline editoriale esterna è
  dismessa [...] un eventuale nuovo workflow verrà progettato da zero dentro i
  confini di questo progetto" | dovrà dire: che il workflow esiste ed è il
  team a quattro ruoli, con link a `docs/WORKFLOW_ORCA.md` | quando: dopo
  approvazione

## STATUS.md

- `STATUS.md:38-40` (sezione "Pipeline Editoriale") | oggi dice: "La vecchia
  catena esterna è dismessa; qualsiasi futura pipeline verrà progettata e
  implementata da zero in modo autonomo" | dovrà dire: lo stato reale del
  rollout (pilota ter-12, quante schede approvate), aggiornato ogni volta che
  lo stato cambia, come fa già il resto del file | quando: dopo approvazione,
  e poi ad ogni avanzamento reale (STATUS.md si aggiorna sempre, non è un
  documento che si scrive una volta)
- `STATUS.md:95` già registra correttamente la contraddizione trovata dalla
  revisione avversaria sul vecchio `nmaiese/redazione-ai`: nessuna modifica,
  è la riga che spiega perché REVIEW.md e content/STYLE.md sotto vanno
  corretti

## REVIEW.md

Il file intero descrive un processo che nomina un repository esterno
dismesso e un Agent Team che non esiste più. Non è una riga isolata, è
l'impianto del documento, e la sezione 1 del piano lo dice esplicito: il
vecchio Agent Team è il caso studiato per non ripeterlo.

- `REVIEW.md:7` | oggi dice: "le PR `automation/*` (pezzi scritti dalla
  catena o dall'Agent Team)" | dovrà dire: le PR del team a quattro ruoli,
  aperte da `scripts/orca_review.py` con `Closes #<issue>` | quando: subito,
  già falso oggi (l'Agent Team è stato tolto dal repo, `git show
  9730a3fc:docs/RIPARTENZA.md`)
- `REVIEW.md:13-14` | oggi dice: "`motore verifica divarioitalia <codice>
  --bozza ...`, nel repo della redazione" | dovrà dire: il comando della
  guardia deterministica unica del cantiere 3, dentro questo repository |
  quando: subito per la parte "nel repo della redazione" (contraddice
  l'autonomia del progetto dichiarata in CLAUDE.md), il nome del comando vero
  solo dopo che il cantiere 3 esiste
- `REVIEW.md:30` | oggi dice: "le quattro guardie di `motore verifica`" |
  dovrà dire: la guardia deterministica sola del cantiere 3 (cifre, link
  canonici, marcatori dei grafici, assoluti tipografici) | quando: dopo
  approvazione, quando la guardia nuova esiste
- `REVIEW.md:38-42` | oggi dice: "quello che ha mosso il `redattore`" e "il
  corpo della PR porta la scaletta" | dovrà dire: lo scrittore del nuovo
  team, e che la forma dell'articolo è libera (sezione 3 bis del piano), non
  una scaletta fissa da controllare voce per voce | quando: dopo approvazione
- `REVIEW.md:44` | oggi dice: "nessun termine da statistico [...] massimo
  mille parole" | va verificato contro il brief nuovo (sezione 3 del piano):
  il tetto di mille parole non è nel piano, va deciso se resta o se lo
  sostituisce la guardia sulle sezioni | quando: dopo approvazione, decisione
  aperta per chi scrive il cantiere 1
- `REVIEW.md:48-51` | oggi dice: "Struttura richiesta dal proprietario:
  notizia nel lead [...] un confronto con un indicatore imparentato" | dovrà
  dire: che non c'è più una struttura a fermate fisse da controllare, il
  revisore boccia titoli-etichetta e sezioni di cautele generiche (sezione 3
  bis del piano) | quando: dopo approvazione, contraddice direttamente la
  decisione "nessuna sezione predefinita"
- `REVIEW.md:75-79` | oggi dice: "Oggi: Nello a mano, con `motore verifica`
  (nel repo della redazione) come primo filtro [...] Prossimo passo: lo
  stesso contratto eseguito da un agente su ogni PR" | dovrà dire: che il
  prossimo passo è già il piano, un revisore lanciato da Orca su ogni PR
  (sezione 2 e 4 del piano) | quando: subito per "nel repo della redazione",
  dopo approvazione per il resto

## content/STYLE.md

- `STYLE.md:7-11` | oggi dice: "Le pagine indicatore, `content/indicators/`,
  non si scrivono da qui. Il loro contratto e' `REDAZIONE.md` del repo
  `nmaiese/redazione-ai`, e chi scrive carica la skill `voce`" | dovrà dire:
  che le pagine indicatore seguono `docs/INDICATOR_PAGES.md` e, per il team
  nuovo, il brief e le skill di `skills/editorial-team/` dentro questo
  repository | quando: subito, già falso oggi. Contraddice l'autonomia del
  progetto dichiarata in CLAUDE.md ("non dipende da quadri centralizzati
  esterni") ed è la contraddizione che la revisione avversaria del 28
  settembre ha già trovato (`STATUS.md:95`)
- `STYLE.md:61-63` | oggi dice: "chi scrive è l'agent `narratore` del repo
  `nmaiese/redazione-ai`" | dovrà dire: lo scrittore del team nuovo (Claude
  opus, worker Orca) | quando: subito per il riferimento al repo esterno,
  dopo approvazione per il nome del ruolo
- `STYLE.md:85-88` | oggi dice: "Chi scrive le pagine indicatore non legge
  questo file: carica la skill `voce` di `nmaiese/redazione-ai`" | dovrà
  dire: il contrario, lo scrittore del team nuovo legge proprio questo file
  perché non esiste più una skill esterna che lo sostituisca, salvo si porti
  `voce` dentro `skills/editorial-team/` | quando: subito per la parte del
  repo esterno, la decisione su dove va `voce` è aperta per il cantiere 1
- `STYLE.md:252-253` | oggi dice: "quello che ferma un pezzo sono le quattro
  guardie di `motore verifica` nel repo della redazione" | dovrà dire: la
  guardia deterministica unica del cantiere 3, in questo repository | quando:
  subito per il repo esterno, dopo approvazione per il nome esatto

## docs/INDICATOR_PAGES.md

- `INDICATOR_PAGES.md:17` | oggi dice: "Quattro sezioni in ordine fisso, un
  unico blocco di prosa" | dovrà dire: che le schede possono avere quattro
  sezioni fisse (le circa 300 esistenti) oppure una forma libera (le schede
  nuove), e rimandare alla sezione "La forma libera" più sotto nello stesso
  file | quando: dopo approvazione. È anche una contraddizione interna
  esistente oggi: la riga 17 dice "quattro sezioni in ordine fisso" e la
  riga 292 dello stesso file descrive la forma libera come già in
  produzione (usata da ter-901)
- `INDICATOR_PAGES.md:211-224` (sezione "L'articolo: quattro ruoli") | oggi
  dice: "Ordine fisso [...] La struttura è uniforme su tutte le pagine" |
  dovrà dire: che questo è il default per le circa 300 schede esistenti, non
  la sola forma possibile, con un rimando esplicito alla forma libera |
  quando: dopo approvazione
- `INDICATOR_PAGES.md:290` | oggi dice: "Lo garantisce
  `ProseStaysOnTheLevelItWasWrittenFor` in
  `tests/integration/test_indicator_texts.py`" | dovrà dire: il nome del
  test vero, dove sta oggi quella garanzia (il file non esiste più) |
  quando: subito, già falso oggi
- `INDICATOR_PAGES.md:377-383` (sezione "Scrivere un articolo") | oggi dice:
  "Non esistono oggi un dossier, un brief o una coda automatici da
  eseguire" | dovrà dire: che il team a quattro ruoli produce un `brief.md`
  e un `dossier.json` per ogni indicatore in lavorazione (sezione 3 del
  piano), con link a `docs/WORKFLOW_ORCA.md` | quando: dopo approvazione
- `INDICATOR_PAGES.md:477-496` (sezione "Che cosa è verificato e che cosa
  no") | oggi dice: "`tests/integration/test_indicator_texts.py` copre la
  parte meccanica" e elenca i controlli attivi | dovrà dire: dove sono
  davvero oggi quei controlli (il file citato non esiste) e, dopo il piano,
  quali di quei controlli confluiscono nella guardia unica del cantiere 3 |
  quando: subito per l'esistenza del file, dopo approvazione per il resto
- `INDICATOR_PAGES.md:530-538` (su `scripts/prose_lint.py`) | resta corretto
  come descrizione tecnica dello script. Da verificare solo se il cantiere 3
  lo assorbe nella guardia unica o lo lascia com'è (non fa fallire niente,
  conta soltanto) | quando: dopo approvazione, decisione aperta
- `INDICATOR_PAGES.md:684-688` (comandi di verifica) | oggi dice il comando
  `.venv/bin/python -m unittest discover -s tests -v`, che non è
  `bin/py` come impone il resto del repo | non è una riga che il piano
  tocca, ma è un'incoerenza preesistente da segnalare visto che si riscrive
  la pagina | quando: subito, indipendente dal piano

## docs/WORKFLOW_ORCA.md

- `WORKFLOW_ORCA.md:107` | oggi dice: "**Un task, un worktree, un agente.**
  Due agenti nello stesso checkout non si coordinano, e Orca non li blocca"
  | dovrà dire: la deroga che il piano chiede esplicitamente (sezione 5,
  punto 1 di `PIANO.md`): nel worktree di un indicatore più ruoli si
  succedono (scout, scrittore, grafico), uno che scrive alla volta, e il
  revisore nasce sempre in un worktree diverso. La regola di fondo (un
  worker non esce dal proprio worktree, niente coordinamento fra due agenti
  vivi insieme) resta valida, va solo detto che "un agente" oggi significa
  "un agente alla volta" per gli indicatori | quando: dopo approvazione,
  è la voce più importante del cantiere 1 perché oggi la regola è scritta
  come assoluta e il piano la contraddice apertamente
- `WORKFLOW_ORCA.md:1-8` | il documento non nomina ancora il flusso a
  issue/PR/revisore del piano. Andrebbe una riga di rimando a
  `docs/design_drafts/team/PIANO.md` finché il cantiere 1 non lo assorbe
  per intero, o alla sezione nuova quando il cantiere è scritto | quando:
  dopo approvazione
- Il quarto difetto di Antigravity (il prompt che arriva prima che
  l'interfaccia sia pronta) **è già documentato**, `WORKFLOW_ORCA.md:226-229`
  punto 4. `PIANO.md:233` lo elenca ancora come da aggiungere: è il piano
  che va corretto, non questo file, oppure la riga del piano si toglie
  quando si scrive il cantiere 1 | quando: nessuna azione su questo file

## docs/WORKFLOW_ARTICOLI_TREND.md

- `WORKFLOW_ARTICOLI_TREND.md:7-12` | oggi dice: "Questo documento descrive
  un processo storico [...] non costituiscono oggi una pipeline editoriale
  operativa" | corretto e non cambia: il piano riguarda le schede
  indicatore, non gli articoli del blog guidati dai trend, e il piano lo
  dice esplicitamente (sezione 0: "non un pezzo del blog") | quando: nessuna
  azione, salvo se in futuro il team si estende al blog
- Nessun'altra riga di questo file diventa falsa con l'approvazione del
  piano attuale. Va solo tenuto d'occhio se un cantiere futuro estende il
  team agli articoli del blog, perché oggi i due processi userebbero due
  linguaggi diversi per lo stesso concetto (dossier, brief, guardia)

## docs/SECONDARY_SOURCES.md

Nessuna riga diventa falsa. Il registro delle fonti secondarie resta valido
per lo scout del team nuovo, che lo userà per il contesto (sezione 2 del
piano, "Le dimensioni del brief", parte 5). Nessuna azione.

## docs/FAMIGLIE_INDICATORI.md

- `FAMIGLIE_INDICATORI.md:248` | oggi dice: "sezioni con `role` in
  `{definizione, quadro, dinamica, limiti}`" | è una descrizione dello
  schema attuale di `content/indicators/`, resta vera per le schede
  esistenti e per la forma non libera. Da aggiungere solo un rimando alla
  forma libera se si riscrive questa sezione, non è urgente | quando: bassa
  priorità, dopo approvazione se si tocca comunque il file
- `FAMIGLIE_INDICATORI.md:281` | oggi dice: "Pipeline editoriale: quella
  esterna è dismessa; un eventuale nuovo workflow verrà progettato da zero
  all'interno del progetto" | stessa correzione delle altre occorrenze |
  quando: dopo approvazione

## content/esempi/README.md

Nessuna riga diventa falsa con l'approvazione del piano. Le citazioni di
"rubrica a 19 su 20" (riga 16) e "criterio 8 della rubrica" (righe 62, 118)
sono citazioni storiche di una misura passata, non un contratto vivo, e il
piano non le contraddice: la rubrica del revisore nuovo è diversa (criteri
passa/non passa più il divieto ai titoli-etichetta, sezione 3 del piano) ma
questo file non descrive quella rubrica, la nomina di striscio. Nessuna
azione salvo il cantiere 5 (la rubrica del revisore vive in
`03_diagnosi_qualita.md`, non qui).

## .claude/rules/editorial.md

- `editorial.md:28` | oggi dice: "un `lead` più quattro sezioni ordinate
  (`definizione`, `quadro`, `dinamica`, `limiti`)" | dovrà dire: che è lo
  schema delle schede esistenti, e che le schede nuove del team usano la
  forma libera, con rimando a `docs/INDICATOR_PAGES.md` | quando: dopo
  approvazione
- `editorial.md:18-19` | oggi dice: "Un articolo non si misura con una
  rubrica a punti: quella è stata ritirata il 4 settembre insieme al lint
  della prosa. La vecchia verifica automatica esterna è dismessa" | resta
  vero per il principio (niente rubrica a punti sulla prosa), ma "la vecchia
  verifica automatica esterna è dismessa" convive male con
  `content/STYLE.md` che ancora nomina un contratto esterno vivo: le due
  righe raccontano stati diversi dello stesso fatto | quando: subito, per
  coerenza con la correzione di `content/STYLE.md` sopra

## .github/ISSUE_TEMPLATE

- `.github/ISSUE_TEMPLATE/config.yml:4` | oggi dice: il link per le proposte
  editoriali punta a `https://github.com/nmaiese/redazione-ai/blob/master/QUADRO.md`,
  "il Quadro della redazione", con "il gate di Nello" li' | dovrà dire: un
  percorso dentro questo repository, per esempio la lista di indicatori
  approvata di cui parla `PIANO.md` sezione 1 punto 5, o la issue con label
  `run:team` | quando: subito, già falso oggi. Stessa contraddizione con
  l'autonomia del progetto trovata in `content/STYLE.md` e `REVIEW.md` sopra
- `.github/ISSUE_TEMPLATE/routine-fermata.md:16` | oggi dice, nel commento
  guida: "Il passo della catena della redazione: coda, brief, ricercatore,
  scrittore, verificatore, pubblica, pr" | dovrà dire: i passi del flusso
  nuovo (issue, scout, scrittore, grafico, guardia, PR, revisore, Nello) una
  volta scritto il cantiere 1, o un elenco generico finché non lo è | quando:
  subito per il fatto di nominare la catena della redazione esterna, la lista
  esatta dopo approvazione

## .claude/hooks/pre_compact.py

- `pre_compact.py:32` | oggi stampa a ogni compattazione "la vecchia pipeline
  editoriale esterna e' dismessa" come unico promemoria sul tema | resta vera
  anche dopo il piano, perché il team nuovo non è la vecchia catena esterna:
  non serve correggerla | quando: nessuna azione, salvo valutare se aggiungere
  una seconda riga di promemoria sul team attivo dopo l'approvazione

## Fuori dal repository, sola lettura

- `~/dev/dev-tools/claude/CLAUDE.md`: nessuna riga nomina Divario Italia o
  la sua pipeline editoriale, quindi nessuna riga diventa falsa. Non è un
  file che questo repository può modificare comunque (regola globale: si
  modifica nel repo `nmaiese/dev-tools`)
- `~/dev/dev-tools/docs/orca.md`: descrive il protocollo Orca generale, non
  i ruoli specifici di un repository. Non contraddice il piano: la tabella
  dei ruoli per divarioitalia sta già, correttamente, in
  `docs/WORKFLOW_ORCA.md` e non qui. Nessuna azione, e comunque non
  modificabile da questo repository

## Contraddizioni fra documenti, oggi

1. `CLAUDE.md` dichiara l'autonomia del progetto ("non dipende da quadri
   centralizzati esterni") mentre `content/STYLE.md:8` e `REVIEW.md:13-14,
   75` rimandano il contratto delle pagine indicatore e la guardia a un
   repository esterno (`nmaiese/redazione-ai`) che le istruzioni globali di
   Nello (`~/dev/dev-tools/claude/CLAUDE.md`) non citano nemmeno come
   dipendenza attiva. Già trovata dalla revisione avversaria del 28
   settembre (`STATUS.md:95`), non ancora corretta nei file.
2. `docs/INDICATOR_PAGES.md:17` dice "quattro sezioni in ordine fisso" e lo
   stesso file, riga 292, descrive la forma libera come meccanismo già in
   produzione dal 6 settembre 2026, usato da ter-901. Le due righe si
   leggono come se il documento non sapesse di se stesso.
3. `docs/WORKFLOW_ORCA.md:107` ("un task, un worktree, un agente", assoluto)
   contro `PIANO.md` sezione 4, punti 3-5, che mette scout, scrittore e
   grafico nello stesso worktree in sequenza. Non è ancora una
   contraddizione scritta, perché il piano non è approvato, ma lo diventa
   nell'istante in cui il primo worker del team parte senza che
   `WORKFLOW_ORCA.md` porti la deroga.
4. `REVIEW.md` e `docs/WORKFLOW_ARTICOLI_TREND.md` usano due lessici diversi
   per lo stesso concetto (guardia bloccante prima della review): il primo
   parla di "motore verifica" e "quattro guardie", il secondo di "verify" e
   dei test di `test_blog_trend_articles.py`. Non è un errore, sono due
   pipeline diverse (schede indicatore contro articoli del blog), ma un
   lettore che non lo sa può pensare che siano lo stesso meccanismo.
