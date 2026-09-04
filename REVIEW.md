# REVIEW.md — i passaggi di review su ogni PR

Ogni PR riceve gli stessi passaggi, nello stesso ordine, con i finding
ordinati per gravità. Chi li esegue (un agente di review o una persona)
riporta solo finding, non riscrive. Nello legge i finding e giudica intento
e rischio: il merge resta suo (Gate B). Le PR `automation/*` (pezzi scritti
dalla catena o dall'Agent Team) passano tutti e tre i passaggi; le PR di
codice il primo solo se toccano `content/`.

## Passaggio 1 — Cifre e fonti (blocca)

- Ogni numero nel testo esiste nel dossier dell'indicatore o è un
  `{{fact:id}}` risolto (`bin/py -m lab.controlla <codice> --bozza ...`,
  `uv run motore validate <file>` in platform). Una cifra senza anno, un
  trend nella direzione sbagliata, un confronto fra livelli diversi
  (regione contro provincia) sono `alta`.
- Ogni fonte esterna ha URL che risponde, data, e dice davvero ciò che il
  testo le attribuisce. Una fonte che non regge è `alta`; una fonte senza
  data è `media`.
- Percezione presentata come fatto, conteggi ("N regioni salgono") non
  ricalcolati sui dati, parenti di tema descritti in blocco (#203): `alta`.

## Passaggio 2 — Regole editoriali (blocca sui pavimenti)

- `content/STYLE.md` e la rubrica `docs/WRITING_RUBRIC.md`: dieci criteri su
  quattro assi, un asse sotto il pavimento boccia (`alta`); sotto 14/20 non
  è pronto (`alta`).
- Assoluti: niente em-dash, en-dash, `;`, `…`; nessun termine da statistico
  (bontà del raggruppamento, mediana, spread, coefficiente di variazione,
  quantile, deviazione standard); massimo mille parole; link canonici agli
  indicatori. Violazioni: `media`, `alta` se più di due.
- Struttura richiesta dal proprietario: notizia nel lead con la conseguenza
  per chi vive lì; il perché con una fonte esterna datata; che cosa cambia
  per le persone; un confronto con un indicatore imparentato. Un elemento
  mancante è `media`; il perché assente è `alta`.

## Passaggio 3 — Igiene e sicurezza (blocca)

- Nessun segreto, token o `.env` nel diff (`alta`).
- Una PR `automation/*` tocca solo `content/`, `data/lab/`,
  `.claude/agent-memory/` e l'intent in platform. File di test, hook,
  rules, `app/` toccati da una run automatica: `alta` (separazione dei
  poteri, regola 4 di platform).
- Commit senza trailer `Co-Authored-By`; branch da `master`, mai su
  `master` (`bassa`, ma si corregge prima del merge).
- CI verde (`python`, `frontend`): obbligatoria, non è un finding.

## Gravità e regole

- `alta`: si corregge prima del merge, sempre.
- `media`: si corregge prima del merge salvo decisione esplicita di Nello
  nel commento di merge.
- `bassa`: al massimo cinque per review; oltre, si tacciono.
- Non si segnalano: formattazione, ordine delle chiavi nei JSON, sinonimi.
- Un finding che si ripete in due PR diventa una riga in `CLAUDE.md`, una
  regola in `.claude/rules/`, o un caso in `evals/golden/` di platform
  (regola 6 di platform: documentazione sincrona).

## Chi esegue

Oggi: Nello a mano, con `motore validate` e `lab.controlla` come primo
filtro deterministico (il commento automatico di `editoriale.sh`). Prossimo
passo: lo stesso contratto eseguito da un agente su ogni PR (plugin
`code-review` o `claude-code-action` in CI), così i tre passaggi sono
identici per tutte le PR e la persona legge solo i finding.
