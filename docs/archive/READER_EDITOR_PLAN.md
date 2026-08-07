# Piano corretto: reader-editor (giudice di leggibilità indipendente)

> Revisione critica del piano "lettura più facile per l'utente comune", verificata
> contro il codice reale. Questo file è una **proposta**, non codice fuso. Le tre
> decisioni aperte in fondo cambiano cosa si costruisce e vanno chiuse prima di
> scrivere l'agente.

## Cosa regge del piano originale

- La diagnosi è corretta e verificata: il produttore scrive+valuta+firma la
  leggibilità, nessun giudice indipendente; `definizione` è sempre il primo H2,
  quindi la metodologia apre l'articolo (`eur-rd_p_persreg` ne è la prova).
- Il verdetto legato a `prose_fingerprint` (scade alla riscrittura) è il
  meccanismo giusto e riusabile.
- read-only, store append-only isolato, `soft` (non blocca il merge): topologia
  corretta, due critici paralleli a valle del produttore (leggibilità + fatti).

## Le quattro correzioni critiche (verificate nel codice)

### C1. "L'assenza di verdetto è la coda, gratis" — FALSO come scritto

Il piano assume che, come per il verificatore, la sola assenza di un verdetto
reader-editor metta i 300 articoli in coda. Non è così. La coda del verificatore
**non** è "assenza di verdetto": è **`REQUIRED_STAGES` + scadenza-fingerprint che
lavorano insieme**. Quando la fingerprint scade, `verificatore` non viene mai
aggiunto a `completed_stages` (`practice_timeline.py:251`), quindi
`required ⊄ completed`, `_state_of` esce da `pubblicata`, e `ready_stage`
ri-emette `verificatore`. La fingerprint da sola **non accoda niente**: scade
soltanto uno stadio che era già richiesto.

Conseguenza dura, verificata: `ready_stage` ritorna `None` per lo stato
`pubblicata` (`practice_timeline.py:536`), e i 300 articoli sono terminali lì. Il
reader-editor eredita gratis la **scadenza**, non l'**enqueue**.

**Tre opzioni per accodare i 300 (con costo reale):**

- **(a) `reader-editor` in `REQUIRED_STAGES`.** Ogni pubblicato esce da
  `pubblicata` finché non è letto. `_reached_publication` tornerebbe `False` per
  tutti e 300, e `state=="pubblicata"` è consumato da
  `pipeline_monitor.py:246,274` (`publication_done`): il conteggio "pubblicate"
  del cruscotto `/_pipeline` crolla da un giorno all'altro, per zero guadagno
  funzionale. `practice_timeline --check` (righe 397-405) riporterebbe divergenza
  su tutto il catalogo finché non si riscrive lo stato. **Scartata.**

- **(b) Ramo in `ready_stage` prima della riga 536.** `pubblicata` smette di
  essere terminale. Cambia una semantica di stato usata altrove; ripple diffuso.
  **Scartata a favore di (c).**

- **(c) Quarta lista di voci in `plan_launches` (RACCOMANDATA).** Precedente
  in-repo: `admissions` è già costruito da una coda a monte
  (`pipeline_launch.py:142-156`), fuori da `ready_stage`. Un nuovo
  `scripts/reading_queue.py` fa il diff di `content/indicators/` contro
  `data/pipeline/letture/` per fingerprint e alimenta una quarta lista. **Zero
  cambi alla semantica di stato, zero rietichettatura dei 300, stessa forma di un
  ruolo esistente.** `pubblicata` resta terminale e i 300 restano pubblicati.

  `reading_queue.py` emette **due** tipi di lavoro, entrambi bypassando la
  terminalità di `pubblicata`:
  1. pubblicato senza verdetto reader-editor corrente → lancia `reader-editor`;
  2. pubblicato con verdetto `revise` aperto (fingerprint corrente) → lancia
     `producer` (riscrittura per leggibilità).

  Il produttore riscrive → la fingerprint cambia → **entrambi** i verdetti
  (verifica + lettura) scadono → si ri-accodano da soli. Nessuno stato toccato.

### C2. Non un peso piatto: due flag gradati per gravità

`FLAG_WEIGHT` è additivo ed è un punteggio di **ordine-di-lettura**. Tutti i flag
esistenti marcano un difetto **a livello di frase**, possibile o provato (asse
*correttezza*). La leggibilità è un asse **diverso**: giudizio sull'intero
articolo, fattualmente sano ma illeggibile. Un solo addendo `leggibilita` nella
stessa somma collassa due assi in un numero — proprio ciò che il reader-editor
esiste per evitare ("assi separati, mai una media unica").

Inoltre lo schema **grada già per gravità** (`definizione`=50 vs `mestiere`=15), e
il reader-editor produce già la gradazione: `revise` porta `hard_failures[]`
distinti dai criteri soft. Un peso piatto la butterebbe via.

**Design: due flag.**

| flag | quando | banda | perché lì |
|---|---|---|---|
| `leggibilita_grave` | `revise` con ≥1 `hard_failure` | ~46 | il lettore comune non capisce la pagina. Ma **sotto** `smentita`=60 e `definizione`=50 ("misinforma" batte "confonde"), pari/sopra `rilettura`=45 |
| `leggibilita` | `revise` solo criteri soft | ~22 | prosa rigida ma vera: cede a ogni sospetto fattuale, batte i cosmetici (`mestiere`=15, `eco`=10) |

Rispetta i tre vincoli in tensione: (a) assi separati (gradazione dalla propria
gravità); (b) l'invariante di `review_queue.py:114-139` (frase falsa/mal-definita
batte una brutta); (c) leggibilità primaria (un hard failure sale alto, sopra la
maggior parte dei sospetti-di-rischio). **I numeri esatti (46, 22) si pinnano sul
gold set**, come `definizione`=50 fu "decided by counting"; la banda è ciò che si
decide ora. → **DECISO** (design a due flag).

### C3. Il ping-pong producer↔reader-editor costa due run opus, non una

Ogni round di leggibilità è **producer + verificatore**, non solo producer: la
riscrittura cambia la fingerprint, che fa scadere *entrambi* i verdetti
(`practice_timeline.py:243` e `:251`). Un indicatore che non converge brucia due
run opus per tick, per sempre, senza sorveglianza. Il piano lo sottovaluta
("throughput-bound, non un pavimento").

**Il freno vive nella coda, non nel prompt** (un cap nel prompt non è
imponibile, e il perimetro del cancello esiste proprio perché i prompt non
allargano né restringono i contratti): `reading_queue.py` parcheggia un codice
dopo K round `revise` con una bandiera, e smette di ri-lanciare il produttore per
leggibilità su quel codice finché non interviene altro (nuovo vintage, ecc.).

### C4. Doppio lancio del produttore su un lanciatore con bug noto

Con (c), il produttore può essere lanciato da **due** sorgenti nello stesso tick:
`ready_stage` (es. `stale_vintage`) e `reading_queue` (`revise`). Il lanciatore ha
già il bug noto di non deduplicare le run in volo (memoria
`launcher-inflight-dedup`, ~242k/tick). Va deduplicato **per `code` tra le liste
di voci prima dell'emissione**, almeno entro il tick. Cheap, e appartiene a questo
slice, non differito.

## Meccaniche da non dimenticare (silenziose se saltate)

- **Tre namespace distinti**, da scegliere esplicitamente tutti e tre: nome file
  agente / ruolo / stage. Precedente: `indicator-verifier` (file) ↔ `verificatore`
  (stage) ↔ `AGENT_OF_ROLE`. Proposta: file `reader-editor.md`, ruolo/stage
  `reader-editor`, agente `reader-editor`.
- **Barra finale** sulla costante di perimetro: `LETTURE = "data/pipeline/letture/"`.
  `.claude/rules/pipeline.md`: "la barra finale distingue directory da file, ed è
  ciò che impedisce la fuga."
- **`agent_guard.py` nel frontmatter** del nuovo agente: hook PreToolUse +
  Stop/SubagentStop con `--stage reader-editor` (come `indicator-verifier.md`). Il
  piano copriva `STAGE_PATHS` ma non la guardia per-gesto.
- **`STAGE_PATHS["reader-editor"] = (LETTURE, RUN_JOURNAL)`**; NON in
  `ROLES_THAT_SIGN`; NON in `MERGE_POLICY` come blocco (soft).
- **Bootstrap canary**: un ruolo nuovo non ha baseline contro cui essere "pari".
  `admissions` ha una `evals/admissions/cases.json` scritta a mano. Il
  reader-editor ha bisogno di un gold set autoriale `evals/reader-editor/cases.json`
  con `eur-rd_p_persreg` come `revise` atteso. "Soglia calibrata dal canary" è
  fattibile solo così: la soglia si sceglie sul gold set, non nel vuoto.

## Cosa giudica il reader-editor

Sette criteri 0-2, giudizio LLM non regex, assi separati (mai una media unica):
`comprehension, focus, reader_relevance, search_intent_coverage, cognitive_load,
technical_translation, structure, unique_value`. Più `hard_failures[]` e
`revision_notes[]`. Hard-failure (i più netti): il lead richiede metodologia; la
tesi non è identificabile; non si capisce cosa misuri il dato; una sezione esiste
solo per riempire lo schema; un tecnicismo decisivo non è spiegato; carico
numerico eccessivo in un paragrafo; articolo intercambiabile con un altro
indicatore. Con `soft`, un hard-failure accoda con peso alto, non blocca.

## Store e binding

Un file per lettura in `data/pipeline/letture/`, nome
`{code}__{level}__{fingerprint}.json`, legato a
`verification_queue.prose_fingerprint`. Validazione `row_problems` sul modello di
`verification_queue`. La riscrittura lo fa scadere.

## Come rientrano i 300 (con (c))

Restano `pubblicata`, online a 4 sezioni. `reading_queue.py` li vede senza
verdetto reader-editor → li lancia al reader-editor. `revise` su un tecnico →
`reading_queue` lancia il produttore → riscrive → fingerprint cambia → verifica +
lettura scadono → ri-controllo. Rigenerazione progressiva guidata dalla
leggibilità, senza riscrittura di massa né vintage fasullo, con il freno di C3.

## Ordine di implementazione (canary-gated, un commit per intervento)

1. `reading_queue.py` + gold set `evals/reader-editor/cases.json` (la coda e la
   baseline vengono prima dell'agente).
2. Agente `reader-editor.md` + `STAGE_PATHS` + `agent_guard` + eval `run_eval.py
   reader-editor`. Canary obbligatorio.
3. Flag `leggibilita` in `review_queue.FLAG_WEIGHT` (peso da Decisione 2) +
   sorgente dai verdetti `revise` correnti.
4. Aggancio in `pipeline_launch.plan_launches` (quarta lista) + dedup per `code`
   (C4) + freno K-round (C3) + hint d'ordine (reader-editor prima del verificatore
   sullo stesso indicatore).

Il blocco "Come leggere il dato", il de-boilerplate H1/title e il resto del piano
originale restano differiti a dopo questo slice, come già deciso.

## Stato implementazione (branch nmaiese/reader-editor) — COMPLETO

Tutti e cinque i pezzi fatti e testati, suite intera verde (1015 test), metro
integro, canary annotato in `docs/CANARY.md` (2026-08-06, baseline 8/8).

1. `scripts/reading_queue.py` (stdlib, 19 unit): coda + store `letture/`,
   scadenza-per-impronta, freno K-round.
2. `.claude/agents/reader-editor.md` (opus, read-only, guard `--stage
   reader-editor`); gold set `evals/reader-editor/cases.json` (4 pass + 4
   revise); wiring gate (`STAGE_PATHS`/`MERGE_POLICY`/`check_readings` append-only
   + invarianti, +7 gate integration); harness eval (`score_reader_editor`,
   `run_eval.py reader-editor`, self-test).
3. Canary: giro pulito del reader-editor sul gold = 8/8, precision/recall 1.0,
   zero falsi pass. Fuga di etichetta nel fixture trovata e corretta
   (`prepare()` toglie `_`, `label`, `code`).
4. Due flag in `review_queue` (`leggibilita_grave`=46, `leggibilita`=22),
   sorgente `reading_queue.open_revisions`, invalidano la firma come `smentita`
   (+4 integration).
5. Aggancio `plan_launches` (quarta lista): reader-editor sugli unread, producer
   sui revise, dedup per code, freno via `to_revise`, hint d'ordine
   (reader-editor prima del verificatore in `ROLE_ORDER`). I 300 restano
   `pubblicata` (+7 unit, +1 gruppo monitor). **Slot riservato** in
   `cap_for_tick` (+4 unit): le letture ereditano la priorita' alta di un
   pubblicato e senza riserva monopolizzerebbero il tick (verificato: 3/3 letture)
   fermando il lavoro fattuale. Con la riserva l'arretrato drena a 1/tick e gli
   altri due slot restano a produrre/verificare. Trovato in review con l'advisor.

**Attriti noti, non chiusi qui:** (a) il tipo-agente `reader-editor` hookato non
puo' scrivere in `evals/out/` (serve una deroga in `agent_guard.py`) — il canary
gira col metodo documentato (subagent con istruzioni reali, no hook); (b) il gold
ha 8 casi netti, non vede regressioni piccole finche' non si allarga.

## Decisioni chiuse

1. **Meccanismo di coda**: (c) quarta lista in `plan_launches`. I 300 restano
   `pubblicata`, entrano in lista via `reading_queue.py`. Semantica di stato e
   cruscotto intatti. **DECISO.**
2. **Peso leggibilità**: design a due flag (`leggibilita_grave` ~46 /
   `leggibilita` ~22), numeri pinnati sul gold set. Vedi C2. **DECISO.**
3. **Modello del giudice**: `opus`, canary conferma. Indipendenza da prompt +
   read-only + non vedere l'autovalutazione del produttore, non da un tier più
   debole. **DECISO.**
