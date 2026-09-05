# REVIEW.md — i passaggi di review su ogni PR

Ogni PR riceve gli stessi passaggi, nello stesso ordine, con i finding
ordinati per gravità. Chi li esegue (un agente di review o una persona)
riporta solo finding, non riscrive. Nello legge i finding e giudica intento
e rischio: il merge resta suo (Gate B). Le PR `automation/*` (pezzi scritti
dalla catena o dall'Agent Team) passano tutti e tre i passaggi; le PR di
codice il primo solo se toccano `content/`.

## Passaggio 1 — Cifre e fonti (blocca)

- Ogni numero nel testo esiste nel dossier dell'indicatore o è un
  `{{fact:id}}` risolto (`motore verifica divarioitalia <codice> --bozza ...`,
  nel repo della redazione). Una cifra senza anno, un
  trend nella direzione sbagliata, un confronto fra livelli diversi
  (regione contro provincia) sono `alta`.
- Ogni fonte esterna ha URL che risponde, data, e dice davvero ciò che il
  testo le attribuisce. Una fonte che non regge è `alta`; una fonte senza
  data è `media`.
- Percezione presentata come fatto, conteggi ("N regioni salgono") non
  ricalcolati sui dati, parenti di tema descritti in blocco (#203): `alta`.

## Passaggio 2 — Regole editoriali (blocca sui pavimenti)

- `content/STYLE.md`, e le tre guardie di `motore verifica`: una cifra che non
  sta nel dossier, un link interno che non esiste, una fonte che non risponde
  sono `alta` e fermano il pezzo. Non c'è una rubrica a punti.
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
- Una PR aperta da una run editoriale tocca solo `content/`. File di test,
  hook, rules, `app/` toccati da una run automatica: `alta`, e' separazione
  dei poteri.
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
  regola in `.claude/rules/`, o una Lezione nel Quadro della redazione.

## Chi esegue

Oggi: Nello a mano, con `motore verifica` (nel repo della redazione) come primo
filtro deterministico. Prossimo
passo: lo stesso contratto eseguito da un agente su ogni PR (plugin
`code-review` o `claude-code-action` in CI), così i tre passaggi sono
identici per tutte le PR e la persona legge solo i finding.
