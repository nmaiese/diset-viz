# Piano: la redazione delle schede indicatore, un team orchestrato con Orca

Stato: **approvato da Nello il 28 settembre 2026**, dopo la revisione
avversaria (`06`), il parere del caporedattore (`06b`) e due sue scelte
(decisioni 8 e 9). La prima stesura è nella storia del file, commit `8a94de01`.
Lo stato dell'esecuzione sta in `STATUS.md`.

## Contesto

Nello vuole rifare da zero la pipeline editoriale, con le schede indicatore
separate dal blog, e intanto collaudare l'orchestrazione Orca con GitHub.

Il test completo di oggi, il pilota carceri (`bes:06POL012P`), è uscito "molto
grezzo". Tutti i gate erano verdi, ma il testo era statistica descrittiva a
sezioni fisse, e il titolo poggiava su un estremo non verificato: Fermo al 358%,
che sta in `UNVERIFIED_EXTREMES`. La causa sta nel brief, non nel modello. È lo
stesso errore del vecchio Agent Team: 18-33 $ a pagina, 21 agent, zero pagine
approvate.

Che cosa chiede Nello:
- un team vero, con Claude come team leader
- uno scout dossierista: numeri, fonti esterne, dato recente, anteprime 2026,
  economia delle regioni in cima e in fondo
- uno scrittore dall'italiano impeccabile e discorsivo, che spieghi cosa misura
  l'indicatore, cosa è cambiato e perché, su tutte le dimensioni
- un grafico i cui grafici spieghino il testo
- un revisore della correttezza e della scrittura
- Orca per tutto, con i modelli scelti per quota, carico e qualità
- un worktree isolato per ogni indicatore, con issue e PR
- revisori sempre lanciati da Orca sulla PR o sulla issue
- un articolo senza sezioni predefinite
- i CLAUDE.md aggiornati al nuovo flusso.

### Il materiale di progettazione

È in `docs/design_drafts/team/`, sul ramo `nmaiese/orca-team-test`, con commit
solo locali. Ogni documento l'ha prodotto un modello diverso, usato secondo la
quota.

| file | contenuto | chi |
| --- | --- | --- |
| `01` | ricerca esterna | Antigravity gemini-3.1-pro-high, headless |
| `01b` | casi AI nelle redazioni, 4 URL su 5 verificati con la citazione letterale | Antigravity, headless |
| `02` | audit delle capacità | Codex gpt-5.6-sol high |
| `03` | diagnosi della qualità | Claude opus |
| `04` | flusso Orca/GitHub | Codex |
| `05` | modelli per ruolo | nemotron, gratuito |
| `06` | revisione avversaria: 23 rilievi, 6 bloccanti | Codex gpt-5.6-sol high, worker Orca |
| `06b` | parere del caporedattore | gpt-oss:120b, gratuito |
| `07` | inventario riga per riga dei documenti da aggiornare | Claude sonnet, worker Orca |

Il documento `06` ha cambiato molto. Il piano ne accoglie 20 su 23 così come
sono, e in tre casi diverge per una scelta di Nello.
- **Rilievi 11, 12 e 13.** Codex voleva togliere il secondo scout e il secondo
  parere. Nello ha scelto "largo da subito", quindi restano fissi, ma con tre
  vincoli:
  - li lancia un worker Orca, mai il leader
  - non bloccano
  - il secondo parere risponde solo alle domande 1 e 3, quelle di
    leggibilità, e un disaccordo va a Nello senza aprire un altro giro.
- **Rilievo 20** è accolto nella forma che propone Codex: strumenti su rami non
  uniti, pilota impilato sopra, documenti normativi dopo l'esito. Lo ha scelto
  Nello: prima l'articolo, poi il merge degli strumenti.

## Aggiornamento del 7 ottobre 2026: redazione v2 (gate A e gate B)

Feedback del titolare sul pezzo dei medici di famiglia (PR #353): «troppo numerico, nessun vero insight, non tiene conto di tutti gli indicatori»; gli articoli e le schede devono essere un racconto per il lettore. La redazione resta questa (team, issue, worktree, PR draft, stato nella issue) e si aggiungono due cancelli di sostanza. **Dove il resto di questo documento dice altro, vale questa sezione**: in particolare «Nessun Gate A» (flusso, passo 1), «tre giri» (passo 8 e regole di stop: ora due), il divieto di worker Antigravity e OpenCode e il lancio «solo in headless» (oggi si lancia con `orca-lancia.sh`, mai headless, modelli secondo `MODELLI.md`) e «nessun ruolo oltre i quattro» (si aggiungono il caporedattore del gate A e il verificatore del gate B). La spec completa, con la prova sui medici, sta in `REDAZIONE-divario-v2.md` (fuori dal repo, `orca/specs/`); qui sotto i requisiti, che sono la norma.

### Gate A, prima della scrittura
Il leader Claude scrive `lavoro/<chiave>/brief.md`: domanda del lettore, tesi provvisoria, almeno un insight e tre indicatori realmente incrociati. Astra giudica in contesto nuovo, di famiglia diversa dal brief. Tre classifiche affiancate non bastano.
Lo scout estende il dossier a tutti gli indicatori dello stesso tema e ai pertinenti dei temi vicini. Oggi `brief.build(code)` tratta una scheda: ripetere `scripts.editoriale.brief` per codice in `dossier-<codice>.json` conserva compatibilità con la guardia. Estendere successivamente brief.py, non creare pacchetto_tema.py.
Elenco da `indicator_universe.all_indicator_refs()` e viste, province comprese. `copertura.csv`: codice, nome, tema, livello, anni, inclusione/esclusione motivata. Le matrici delle viste contengono le serie complete, `projection()` le riduce. Salute ha 59 riferimenti, ma medici e rinunce stanno in Mobilità. `theme_categories.csv` è vuoto salvo intestazione, la tassonomia vive in `app/taxonomy.py`.
Insight verificabile, tutte le condizioni necessarie:
1. Corregge esplicitamente una lettura della sola classifica e risponde alla domanda del lettore.
2. Incrocia tre misure pertinenti su anni comuni, stesso livello e popolazioni compatibili. Nessun indicatore ornamentale o gemello contato due volte.
3. Ha formula, righe o chiavi delle osservazioni, numerosità ed esclusioni in `numeri.md`.
4. Distingue risultato e causa: meccanismo candidato documentato oppure ignoto dichiarato.
5. Resiste a un controllo contrario scelto prima del calcolo, per esempio anno alternativo o esclusione dell'estremo. Si conservano anche risultati negativi.
`gate-a.md`, sotto `lavoro/<chiave>/`: SHA e hash del brief, autore/modello, giudice/modello, domanda, tesi, codici e confronto, tabella `criterio | sì/no | prova | limite`, esito PASSA/FERMO, motivo, correzione, destinatario, data. Un no ferma lo scrittore. Un solo ritorno mirato al leader, poi archivio se ancora insufficiente. Label gate-a soltanto dopo PASSA, invalidata da modifiche alla tesi.

### Gate B, in revisione
Alle cinque domande del PIANO si aggiungono quattro controlli binari con citazioni della bozza: T, tesi sostenuta dalle prove. R, confronto fra due territori reali che fa avanzare il racconto. L, significato concreto per il lettore nei primi due paragrafi. N, risultato non ovvio e controllo contrario riconoscibili.
Persone solo da fonti citate, mai inventate o composite. Nessuna scena individuale dedotta da medie. Causa ed effetto solo se documentati, altrimenti legame osservato e motivo ignoto. L'ignoto esplicito non penalizza da solo.
| Voto | Regola osservabile, senza media |
| --- | --- |
| 1 | Errore fattuale bloccante, invenzione o causa non provata, oppure zero controlli soddisfatti. Esempio: “In Lombardia mancano medici perché non si investe”, senza prova |
| 2 | Nessun errore bloccante, solo uno o due controlli soddisfatti |
| 3 | Tre controlli soddisfatti. Esempio: incrocio corretto, ma nessuna conseguenza spiegata al lettore |
| 4 | Tutti e quattro soddisfatti, zero bloccanti, limiti vicini alle affermazioni |
| 5 | Come 4, più controesempio spiegato nella prosa e nessun paragrafo fatto soltanto di valori o ripetizioni del cruscotto |
`lavoro/<chiave>/gate-b.md`: SHA/hash della bozza, famiglie autore/revisore, T/R/L/N con citazioni, controllo anti-invenzione, voto e motivo, rilievi localizzati, giri, esito PASSA/RISCRIVERE/FERMO. PASSA richiede almeno 4 e zero bloccanti numerici, semantici o visivi. Sotto 4 si riscrive, massimo due giri complessivi di revisione, poi FERMO alla direzione. Dissenso: indicare il controllo controverso, non mediare i voti.
Exit zero delle guardie non risolve i fatti “non verificabili”. Label gate-b riferita allo SHA controllato, HTML aperto prima dell'ok.

### Ruoli e modelli (rotazione del 7/10)
Input/output sotto `lavoro/<chiave>/`. Tabella basata su MODELLI.md letto oggi, quote non misurate.
| Ruolo | Prima / seconda scelta | Input | Output |
| --- | --- | --- | --- |
| Leader | Claude sonnet / fable | dossier, fonti, numeri | brief.md |
| Caporedattore Gate A | Codex gpt-6-astra / Gemini 3.1 Pro High | brief e prove | gate-a.md |
| Scout analista | Codex gpt-6-luna / gpt-6-sol | domanda, catalogo, fonti | dossier, copertura.csv, numeri.md, fonti.md |
| Autore | Claude fable / sonnet, invertiti al pezzo seguente | brief passato, fonti | bozza.md |
| Grafico | Codex gpt-6-luna / Claude sonnet | bozza, dati | grafici.md e risorse assegnate |
| Verificatore Gate B | Gemini 3.1 Pro High / Codex gpt-6-luna | bozza, prove, figure | verifica.md, gate-b.md |
Il coordinatore registra rotazione e modello effettivo nella issue. Astra: un giro circoscritto con battito, mai autore del brief. Verificatore distinto dall'analista, sempre di altra famiglia dall'autore. Un worker editoriale alla volta, niente headless. Pareri aggiuntivi della decisione 8 restano non bloccanti, lanciati dal coordinatore via Orca. Antigravity non riceve --model/--effort dal lanciatore: verificarne l'impostazione effettiva. Un solo ripiego, poi stop. Quote non leggibili: “non letto”. Il 5% Codex giornaliero resta budget indicativo.

### Schede indicatore
Stessi due gate e tre indicatori incrociati. Brief di una pagina, racconto indicativamente 180-350 parole: “che cosa significa per te”. Forma libera, level/vintage corretti, nessuna ripetizione del cruscotto. Grafici dinamici dispersione/ritratto esistenti. Soglie dei gate invariate.

## Decisioni già prese da Nello

1. L'oggetto è la **scheda arricchita**, stessa pagina `/indicatore/...`.
2. Il pilota è su una **pagina ad alto traffico**: ter-12, tasso di
   disoccupazione.
3. Le skill Codex vecchie sono **in quarantena**, già fatto.
4. **Issue, rami e PR sì. Il merge è di Nello**, perché il merge su `master` è
   la pubblicazione.
5. **Revisori sempre agenti lanciati da Orca sulla PR o sulla issue.**
6. **Forma `libera`, senza sezioni predefinite.**
7. **CLAUDE.md e documenti degli agenti aggiornati**, dopo il collaudo.
8. **Largo da subito**: più modelli fin dal pilota. Antigravity fa un giro web
   fisso e gpt-oss dà un secondo parere fisso, entrambi lanciati dai worker Orca.
9. **Prima l'articolo**: il pilota parte dai rami degli strumenti non ancora
   uniti. Nello giudica il testo, poi unisce gli strumenti.

## Il team: quattro ruoli in serie

Un solo worker vivo alla volta nel pilota, più il leader (rilievi 12 e 21 di
`06`). Ogni worker finito si rilascia. Non ci sono worker Orca oltre ai quattro.
Antigravity e gpt-oss sono strumenti che un worker lancia, non ruoli.

| ruolo | dove gira | modello | ripiego (uno, non a cascata) |
| --- | --- | --- | --- |
| Team leader | questa sessione | Claude opus | nessuno |
| Scout dossierista | worker Orca nel worktree dell'indicatore | Claude sonnet medium, con WebSearch e WebFetch | Codex gpt-5.6-sol medium |
| Scrittore | worker Orca, stesso worktree, dopo lo scout | Claude opus high | Codex gpt-5.6-sol high |
| Grafico | worker Orca, stesso worktree, dopo lo scrittore | Codex gpt-5.6-sol high | Claude sonnet |
| Revisore | worker Orca in un worktree **nuovo** sul ramo della PR, di famiglia diversa dallo scrittore | Codex gpt-5.6-sol high | Claude opus, se ha scritto Codex |

**Antigravity e i modelli gratuiti sono fissi**, per la decisione 8. Li lancia
sempre il worker Orca del ruolo, in headless, dentro il suo turno. Per questo
restano sotto un agente nato da Orca (rilievo 11) e non contano come worker in
più sulla RAM: sono processi figli di breve durata.
- **Giro web dello scout.** `timeout 900 agy --model gemini-3.1-pro-high
  --dangerously-skip-permissions -p "<consegna>" --print-timeout 900s < /dev/null
  > lavoro/<chiave>/scout_web.md`, lanciato in parallelo alla sua ricerca.
  Cerca un motore diverso: previsioni 2026, chi ne ha scritto, economia delle
  regioni. Lo scout porta in `fonti.md` solo le voci di cui ha aperto l'URL e
  trovato la citazione, come si è fatto oggi su `01b`, con 4 URL su 5 e un 403.
  Ripiego: `gemini-3.8-flash-high`.
- **Secondo parere del revisore.** `timeout 600 opencode run "<consegna>" -m
  ollama-cloud/gpt-oss:120b -f <articolo> -f <brief> < /dev/null`. Risponde
  solo alle domande 1 e 3, quelle di leggibilità, senza vedere il verdetto del
  revisore. Il revisore riporta risposte e disaccordi nel suo commento. **Non è
  bloccante**, e un disaccordo non apre un altro giro: finisce nella PR per
  Nello (rilievo 13). Ripiego: `ollama-cloud/gemma4:31b`.
- **Lettura cieca** nella valutazione: Claude sonnet e gpt-oss.

Vincoli già misurati:
- OpenCode e `agy` solo headless, sempre con `timeout` e `< /dev/null`
- GLM-5.3-Flash fuori fino al rinnovo
- Zen gratuiti mai sul percorso critico.

**Quota protetta prima, non misurata dopo** (rilievo 22):
- prima di aprire la issue si legge la finestra Codex, sullo schermo di una
  sessione Codex aperta apposta (riga "5h limit: N% left"): `agent-probe.sh`
  non dà una percentuale
- sotto il 30% la scheda non parte
- tetto per scheda: scout 1 dispatch con 1 giro `agy`, scrittore 1 dispatch
  più al massimo 1 riparazione chiesta dal grafico più al massimo 2
  riparazioni dopo review, grafico 1, revisore 3, ciascuno con 1 secondo
  parere
- se il modello primario di uno dei quattro ruoli non c'è, si usa un ripiego
  solo e poi ci si ferma. Il giro `agy` e il secondo parere non bloccano: se
  falliscono anche col ripiego, il ruolo va avanti senza e lo scrive nel
  `worker_done`
- **misura del 28 settembre**: tre review Codex gpt-5.6-sol medium sui documenti della fase 1 hanno consumato circa 27 punti della finestra di 5 ore, circa 9 a review. Un lavoro high di scrittura di codice ne consuma di più. La finestra si legge sullo schermo del worker Codex ("5h limit: N% left").

## Lo scout: un contratto con una tabella obbligatoria

Rilievi 16 e 17. Lo scout consegna due file in `lavoro/<chiave>/`.

**`dossier.json`**: deterministico, da `scripts/editoriale/brief.py`.

**`fonti.md`**: una tabella con una riga per voce. Le voci obbligatorie:
- il dato osservato più recente, anche fuori dal catalogo (per esempio l'Istat
  trimestrale)
- le previsioni e anteprime 2026
- l'economia della regione più alta
- l'economia della regione più bassa
- i fattori che muovono l'indicatore
- chi altri ne ha scritto di recente.

Colonne: istituzione, data di pubblicazione, URL aperto, citazione letterale,
limite d'uso. Per le previsioni si aggiungono orizzonte e cautela, perché sono
claim esterni, separati dai dati osservati. Una voce senza fonte si scrive "non
trovato" e non si riempie.

Le fonti nuove le promuove il **leader** nel registro `data/corpus/sources.json`,
dopo il merge. Lo scout non tocca il registro.

## Il brief dello scrittore: materiale, non una scaletta

Lo scrive il team leader in `lavoro/<chiave>/brief.md`, dopo lo scout: le cifre
vengono dal dossier, le cause e l'attualità da `fonti.md`. È l'unico input
numerico dello scrittore, oltre alle cifre dentro le citazioni letterali di
`fonti.md`.

Rilievo 14 e 06b. Le parti non hanno un ordine prescritto, non si mettono in una
posizione e non devono essere tutte usate.

- **Che cosa misura, per una persona normale, in una riga**, con la soglia per
  leggerlo. La scrive il leader e la rilegge Nello sulla issue.
- **La fotografia**: com'è oggi, da dove viene, la forma della serie, chi esce
  dal quadro.
- **Le dimensioni** in cui emerge una differenza. Su ter-12, il genere da ter-175
  e ter-176.
- **Il perché**: le spiegazioni che danno le fonti di `fonti.md`, oppure "non
  spiegato".
- **L'attualità**: dato recente, previsioni 2026, chi ne ha scritto.
- **Un modello di registro** da `content/esempi/`, con il movimento da copiare.

Lo scrittore non riceve:
- le frasi fatte del dossier
- la polarità presentata come giudizio
- le cifre di servizio e i numeri non arrotondati
- il gergo interno
- un angolo già deciso
- una scaletta.

## La forma dell'articolo

- **Sempre `libera`.** Il meccanismo esiste già (`app/indicator_texts.py`,
  `LIBERA`), è usato da ter-901 e non richiede codice.
- **La struttura la decide lo scrittore.** Un titolo va dove il pezzo cambia
  argomento, ed è un'affermazione che la sezione dimostra. Un'etichetta come
  "Il quadro" o "I limiti" non passa.
- **I limiti stanno nella prosa**, dove cambiano la lettura. Non c'è una sezione
  di cautele.
- **I pezzi fissi appartengono alla pagina**, non all'articolo: cruscotto, "Come
  leggere il dato" e apparato.

## Il revisore: cinque domande, rilievi localizzati

Rilievi 13 e 15. Sostituiscono gli 11+6 criteri di `03`.

1. Dal primo paragrafo una persona normale capisce che cosa misura
   l'indicatore e qual è la notizia?
2. Il pezzo spiega perché i numeri sono quelli, con le fonti di `fonti.md`, o
   dice apertamente che cosa non si sa?
3. Si legge come prosa discorsiva, in italiano corretto? Nessun errore di
   grammatica, concordanza, accento o refuso, nessuna frase che regge due idee.
   Non deve essere un elenco travestito, ha titoli-affermazione e nessuna
   sezione di cautele.
4. Ogni affermazione torna con il dossier e con `fonti.md`? Non manca una
   differenza fra dimensioni che cambia la lettura?
5. Ogni grafico è richiamato dal testo e mostra una cosa che il testo dice?

Per ogni "no" il revisore dà la frase citata, il motivo e la correzione minima.
Non fa mappe di paragrafi e cifre, e non chiede sezioni. La domanda 1 è la buona
pratica dell'attacco, non una regola di posizione: non si boccia un pezzo solo
perché la notizia arriva al secondo paragrafo.

Prima di pubblicare confronta `git rev-parse HEAD` con
`gh pr view --json headRefOid`: se sono diversi non pubblica (rilievo 6).

Pubblica sempre con `gh pr review --comment`, con verdetto `DA CORREGGERE` oppure
`PRONTA PER NELLO` e lo SHA, e aggiorna lo stato della issue. Non usa mai
`--approve` né `--request-changes`, perché l'identità è la stessa (rilievo 7).

## I grafici

Rilievi 18 e 19. `docs/INDICATOR_PAGES.md` vieta di ridisegnare nel testo serie,
mappa e classifica, che il cruscotto mostra già. Il grafico sceglie quindi fra:
- i due tipi esistenti, `dispersione` e `ritratto`
- un tipo nuovo solo se mostra una relazione che il cruscotto non ha.

**Nel pilota non si costruiscono tipi di grafico nuovi.** Lo dicono il rilievo 18
e l'audit `02`: prima le storie, poi solo i tipi che servono.

Per ter-12 il candidato naturale è
`<!-- grafico: dispersione con=ter-901 evidenzia=... didascalia="..." -->`:
disoccupazione e PIL pro capite, una regione per punto. È il "perché" in
figura, e non richiede codice. Il renderer di oggi disegna i punti grigi e
accende in arancio le regioni in `evidenzia`: i colori delle ripartizioni
richiederebbero una PR di `app/charts.py`, che nel pilota non si fa.

La differenza donne e uomini (ter-175, ter-176) sulla pagina di oggi è solo un
elenco di link (`dimension_siblings` in `v1/indicatore.html`), non un grafico.
Nel pilota la porta il testo. Un grafico a due punti per regione si costruisce
**dopo** il pilota, solo se la storia l'ha chiesto. In quel caso la PR del
renderer si unisce prima di quella del contenuto.

Ogni figura ha una specifica:
- la provenienza e l'unità
- gli anni e i dati mancanti
- una didascalia che si regge da sola
- la resa a 375 e 768 px
- i temi chiaro e scuro
- l'arancio solo per le regioni in evidenza, mai come colore dei dati.

## Lo stato e la ripresa

Rilievi 10 e 23.

- **La issue è l'unico posto dello stato.** È la sezione `## Stato` nel corpo
  della issue, riscritta sul posto: fase, SHA, prossimo passo, chi lo fa. Non è
  un commento, perché con un'identità sola `gh issue comment --edit-last`
  toccherebbe il commento sbagliato. Label, PR,
  `TASK.md` e scheda Orca sono viste derivate.
- **Ripresa dopo un'interruzione**, con due comandi documentati nel runbook,
  senza script nuovi:
  - `gh issue list -l run:team --json number,title,body`
  - `gh pr list --draft -l run:team --json number,headRefOid,reviews`.

## Il flusso di un indicatore (runbook, rilievi 1-9)

1. **Controlli preliminari.** Si leggono quota e RAM (`free -m`). Poi la issue
   con `gh issue create --label run:team --body-file`: domanda, riga 1 del brief,
   file attesi, sezione `## Stato` del corpo. Dal 7/10 il **Gate A** c'è: `gate-a.md` indipendente deve dare PASSA prima dello scrittore
   (sezione «Aggiornamento del 7 ottobre»), e la label `gate-a` si mette solo dopo.
2. **Worktree senza agente**, così non c'è un secondo coordinatore:
   `orca-ide worktree create --name ind-ter-12 --issue <n> --base-branch origin/<base> --no-parent --setup skip`.
   Non si usa `orca_dispatch.py --role worker`. `<base>` è `master` a regime. Nel
   pilota è l'ultimo ramo degli strumenti (decisione 9).
3. **Scout.** `worker-start --worktree issue:<n> --agent claude --model sonnet`.
   Poi `check --wait`, poi `worker-release`, poi un solo `check --ack <deliveryId>`
   per l'intera delivery. Il leader scrive `lavoro/<chiave>/brief.md` dal dossier e da `fonti.md`, con la figura da proporre se ce n'è una, e ne pubblica una copia sulla issue.
4. **Scrittore.** Stesso schema, parte solo dopo il release dello scout.
5. **Grafico.** Stesso schema, parte solo dopo il release dello scrittore.
6. **Guardia e PR draft.** Il leader lancia la guardia, fa il commit e, finché
   `orca_review.py` non pubblica ancora con `--base` diverso da `master`, apre
   la PR a mano, in **draft**, con `gh pr create --draft --base <ramo-2c>`
   (04, sezione 8): vecchio e nuovo testo, fonti e SHA nel body, più
   `--label run:team` e `Closes #n`.
7. **Revisore.** Prima il worktree, da solo:
   `orca-ide worktree create --name <slug>-review-<n> --repo id:<id> --base-branch origin/<ramo> --no-parent --setup skip`.
   Poi `worker-start --worktree branch:nmaiese/<slug>-review-<n> --agent codex`,
   con lo SHA scritto nella spec (04, sezione 9). Poi `check`, `release` e `ack`.
8. **Riparazione.** Se il verdetto è `DA CORREGGERE`, parte un **nuovo** worker
   scrittore sul worktree dell'indicatore, con i rilievi, lo SHA e i soli file
   autorizzati. Poi guardia, push e un revisore nuovo. Due giri al massimo dal 7/10, poi
   FERMO alla direzione; il Gate B vuole voto almeno 4 e zero bloccanti sullo SHA corrente.
9. **PRONTA PER NELLO.** Solo ora `gh pr ready` e label `gate-b` (rilievo 8).
10. **Merge di Nello, poi pulizia** con `orca_clean.py`. Il leader promuove le
    fonti nel registro e chiude lo stato.

## Esecuzione, in ordine

Rilievo 20: prima gli strumenti su rami e PR, poi un pilota, poi i documenti
normativi.

### Fase 0. Consolidare il piano nel repo

Commit locali, fatti da me.
- Chiudo il run `run_b16a0c77bdaa`: `check --ack delivery_731ecc126c37`, poi
  `worker-release --dispatch ctx_e945a4bfa114`. Il terminale Codex di W6 tiene
  ancora RAM.
- Salvo `01b`, che oggi sta solo nello scratchpad, e `06`, con la nota del
  leader.
- Riscrivo `PIANO.md` su questo piano.
- Riscrivo `04_orca_github.md` come runbook eseguibile: senza Gate A, senza
  dispatcher, con ack, release, SHA e PR draft.
- Aggiorno `STATUS.md`.

### Fase 1. Documenti già falsi oggi, da `07`

Commit su questo ramo. Il passaggio su `master` lo decide Nello, perché il push
su `master` è un deploy.
- `content/STYLE.md` righe 7-11, 61-63, 85-88 e 252-253, via i rimandi a
  `nmaiese/redazione-ai`
- `REVIEW.md`, via "nel repo della redazione" e l'Agent Team
- `docs/INDICATOR_PAGES.md` righe 290 e 477-496, che citano
  `test_indicator_texts.py`, tolto in `eb2c2f72`
- `.claude/rules/editorial.md` righe 18-19.

Lo fa un worker Orca Claude sonnet medium, con `07` come spec. Lo rivede un
worker Orca Codex medium, con un commento sulla issue della fase.

### Fase 2. Strumenti, tre PR impilate, non unite

Sono inerti per il sito. Sono anche il primo collaudo del giro issue, PR e
revisore Orca.

Le PR sono **impilate**:
- 2a parte da `master`
- 2b parte dal ramo di 2a
- 2c parte dal ramo di 2b.

Così ogni diff mostra solo la sua parte e ogni PR ha il suo revisore Orca. Nello
le unisce in ordine **dopo** aver giudicato il pilota (decisione 9), e GitHub
ribasa da solo le successive. Una alla volta, per la RAM e la quota Codex.

Ogni revisore di codice lancia anche lui un secondo parere gratuito, per la
decisione 8: `opencode/nemotron-3-ultra-free` headless sul diff, non bloccante.

| PR | contenuto | autore | revisore Orca |
| --- | --- | --- | --- |
| 2a | `scripts/editoriale/brief.py` e le skill di ruolo | Codex gpt-5.6-sol high per lo script, io per le skill | Claude sonnet |
| 2b | la guardia | Claude sonnet high | Codex gpt-5.6-sol medium |
| 2c | `orca_review.py` esteso | Claude sonnet medium | Codex medium |

**2a, il brief.** Parte da `app/indicator_view.build_indicator_view`. Aggiunge:
- il conteggio sopra soglia e la forma della serie
- le dimensioni: i fratelli da `config/indicator_families.csv`, il gemello di
  livello, le ripartizioni
- l'avviso su `seo_titles.UNVERIFIED_EXTREMES`
- il contesto economico: ter-901, ter-902, ter-13, ter-345
- le cifre già arrotondate.

Riusa `scripts/dump_indicator_stats.py`, lanciato con `-m`. I test girano su
ter-12 e su `bes:06POL012P`.

**2b, la guardia.** Un test in `tests/integration/` più uno script da lanciare
su una bozza, con la CLI fissata da qui: `bin/py -m scripts.editoriale.guardia
<chiave> --dossier <file>`. Controlla:
- le cifre contro il dossier, con il valore assoluto quando la direzione è detta
  a parole: è il difetto di `gate2_verify.py`
- i link canonici
- i marcatori `<!-- grafico -->` che si disegnano davvero
- le sezioni `libera` senza titolo
- em-dash, en-dash, `;` e `…`.

Non conta le sezioni. Riusa `scripts/prose_lint.py` e
`scripts/indicator_store.py`.

**2c, `orca_review.py`.** Aggiunge:
- `--base`, con il conteggio dei commit fatto rispetto a quella base invece
  che a `origin/master..HEAD` (`--draft` c'è già)
- `--label`
- `--body-file`, con il testo prima e dopo da `indicator_store.rendi` e lo SHA.

**Le skill di ruolo, nella PR 2a.** `skills/editorial-team/{scout,scrittore,grafico,revisore}/SKILL.md`,
una pagina ciascuna. Le scrivo io, dal contratto di scout, brief, forma e
revisore scritto qui sopra.

### Fase 3. Il pilota ter-12, impilato su 2c

Si esegue il runbook dal passo 1 al passo 10.
- Il worktree parte da `origin/<ramo 2c>`.
- La PR di contenuto ha come base il ramo 2c, quindi il diff mostra l'articolo
  e i tre file di `lavoro/ter-12/` (dossier, fonti, brief), che il revisore
  legge dal worktree della PR. Con il merge quei file arrivano su `master`:
  se non devono restarci, si decide come toglierli dopo.
- La CI gira già con la guardia nuova.
- **Primo passo:** un worker vivo alla volta.
- **Misure prima e dopo ogni worker:** `free -m`, `swapon --show`, finestra
  Codex.

### Fase 4. La valutazione

- Lettura cieca del vecchio e del nuovo ter-12, da parte di Claude sonnet, di
  gpt-oss e di Nello. Claude sonnet e gpt-oss non appartengono a nessuno dei
  quattro ruoli: la lettura cieca la lancia il team leader in headless, come
  deroga dichiarata alla regola che i modelli gratuiti li lancia sempre un
  worker Orca.
- **Se l'articolo convince Nello**, unisce in ordine 2a, 2b, 2c e poi il pilota.
- **Se non convince**, gli strumenti restano non uniti. Si rilegge il brief e si
  corregge sui rami.
- Poi ter-281, poi una terza scheda, questa volta da `master`. I lotti solo dopo
  tre schede approvate.
- Un grafico nuovo, per esempio donne e uomini, solo se una delle tre storie
  l'ha chiesto.

### Fase 5. I documenti normativi, dopo l'esito del pilota

Dall'inventario `07`:
- `CLAUDE.md`, righe 35 e 137-138: la pipeline c'è, con una guardia sola
- `AGENTS.md`, righe 30-32
- `README.md`, righe 102-104
- `docs/WORKFLOW_ORCA.md`: la deroga "un agente alla volta nel worktree
  dell'indicatore, revisore sempre fuori" e il runbook
- `docs/INDICATOR_PAGES.md` riga 17, righe 211-224 e "Scrivere un articolo"
- `.claude/rules/editorial.md` riga 28
- `docs/FAMIGLIE_INDICATORI.md` riga 281
- la descrizione della label `run:team`, che oggi dice "Agent Team", con
  `gh label edit`
- il template `.github/ISSUE_TEMPLATE/indicatore-team.yml`: i form funzionano
  solo dal ramo di default, quindi nel pilota la issue si apre con
  `--body-file`.

Le istruzioni globali di dev-tools non hanno righe false. La sola aggiunta
proposta è la nota su `< /dev/null` in `~/dev/dev-tools/docs/orca.md`, con l'ok
di Nello, perché è un altro repo.

## Regole di stop

- Due schede respinte su tre: ci si ferma e si rilegge il brief, senza
  aggiungere controlli.
- Più di due giri su un pezzo (dal 7/10, prima erano tre): il pezzo si ferma e va alla direzione.
- Quota Codex sotto il 30%, o swap in crescita con un solo worker: la scheda non
  parte.
- Un gate che blocca tutto si ripara, non si spegne.

## Cosa non fare ancora

- Niente lotti e niente due indicatori insieme.
- Niente Routine né automazioni Orca a orario.
- (SUPERATO il 7/10: oggi si usano tutti i provider con `orca-lancia.sh`, vedi `MODELLI.md`.) Niente Antigravity od OpenCode come worker Orca (`worker-start --agent
  antigravity` o `opencode`). Solo in headless, lanciati dal worker del ruolo
  dentro il suo turno, con `timeout` e `< /dev/null`.
- Nessun ruolo oltre i quattro.
- Niente push su `master` né merge senza Nello.
- Niente CLAUDE.md sul flusso prima del pilota.

## Verifica

- **Fase 1 e fase 5.** Si cercano `redazione-ai`, `test_indicator_texts` e
  "pipeline automatica non è attiva" fuori da `docs/design_drafts/` e dallo
  storico di `STATUS.md`. La ricerca deve tornare vuota.
- **Ogni PR di codice.**
  - `bin/py -m unittest discover -s tests -v` verde, più `git diff --check`, più
    CI su `pull_request`.
  - Il commento del revisore Orca deve portare lo SHA giusto.
- **2b.** La guardia resta verde su ter-901 e su ter-12 com'è oggi. Deve fallire
  su una bozza costruita con un marcatore rotto, una cifra col segno sbagliato
  e una sezione libera senza titolo.
- **Il grafico del pilota.** `DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python
  bin/py -m gunicorn run:app -b 127.0.0.1:5050` dalla radice del worktree del
  pilota, poi ter-12. Il marcatore `dispersione` deve essere reso:
  SVG presente, `figcaption` con i due indicatori e gli anni, 375 e 768 px, tema
  scuro. La guardia 2b deve fallire se il marcatore punta a un indicatore che
  non esiste.
- **Pilota.**
  - Guardia verde e verdetto sulla PR con lo SHA.
  - Pagina resa in locale, con `data-v1` e il grafico visibile.
  - Lettura cieca e misure di RAM e quota nella issue.
  - Il giudizio di Nello.
