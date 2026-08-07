# Archivio

Documenti di **piano**, non di contratto: descrivono un lavoro deciso e ormai
fatto, e nessun file vivo li legge piu'. Restano perche' portano le misure e le
ipotesi cadute che hanno prodotto il codice di oggi, e una misura buttata via si
rifa' da capo. Non sono fonti di verita': se uno di questi contraddice il
codice, ha ragione il codice.

| documento | che cosa conserva | dove vive adesso la materia |
| --- | --- | --- |
| `WRITING_QUALITY_PLAN.md` | il piano sulla qualita' della prosa, il primo lotto misurato e la rubrica applicata a 52 articoli | la voce sta in `content/STYLE.md`, il metro in `docs/WRITING_RUBRIC.md`, il cancello in `officina/lint.py` |
| `EDITORIAL_PRACTICE.md` | l'RFC che ha definito la pratica editoriale (identita', stati, transizioni, la pull request come vista) prima di scrivere il codice. Si apre dicendolo: "Fase A ... non contiene codice, non cambia il comportamento" | il modello vive in `scripts/practice_timeline.py` e `scripts/practice_model.py`, la narrativa della catena in `docs/AUTONOMOUS_PIPELINE.md`, le regole sempre vere in `.claude/rules/pipeline.md` |
| `AUTH_SUPABASE.md` | il piano iniziale del sistema account su Supabase. Si dichiara superato in testa: "Non agire su questo doc: leggi `ACCOUNT.md`" | [`docs/ACCOUNT.md`](../ACCOUNT.md) |
| `READER_EDITOR_PLAN.md` | il disegno del giudice di leggibilita', le quattro correzioni critiche e le tre decisioni chiuse | l'agente e' `.claude/agents/reader-editor.md`, la coda `scripts/reading_queue.py` |
