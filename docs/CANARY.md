# Il giro di canary

Prima di cambiare **modello, prompt, skill, rubrica, hook o permessi** degli
agenti della catena, si misura. Un cambio di questi non rompe mai un test:
cambia il giudizio, e il giudizio non ha una suite. La rete e' questa
procedura, e va fatta PRIMA di fondere il cambio, perche' dopo il primo giro
di Routine il nuovo comportamento e' gia' in pagina.

## 1. Le eval congelate

```bash
python3 evals/score_eval.py --self-test     # il metro e' integro
python3 evals/run_eval.py writer            # poi si fa girare l'agente sul compito
python3 evals/run_eval.py reviewer
python3 evals/run_eval.py verifier
```

Ogni eval stampa il compito da dare all'agente NUOVO (con il modello o il
prompt candidato) e `score_eval.py` misura il risultato. Il confronto e' con
l'ultimo punteggio annotato qui sotto: un punteggio che scende e' un no, non
un dettaglio.

## 2. Il canary set

Dieci indicatori fissi, scelti perche' coprono le famiglie e i casi che hanno
gia' fatto male (definizione ingannevole, due livelli, contextual, esterno):

| codice | perche' e' nel set |
| --- | --- |
| `ter-178` | il riferimento delle eval, serie lunga e regolare |
| `ter-402` | la definizione che ha gia' ingannato (titolari donne, non imprese) |
| `ter-72` | il perimetro nascosto nel titolo (addetti, non imprese) |
| `ter-60` | la rottura di serie non dichiarata |
| `ter-105` | il tasso di turisticita', il link canonico degli esempi |
| `bes-01SAL001` | due livelli territoriali, articolo per livello |
| `bes-10AMB008` | cifre provinciali, che nessuna guardia controlla |
| `dem-OLDAGEDEPR` | il contextual da manuale (dipendenza anziani) |
| `eur-rd_e_gerdreg` | famiglia Eurostat, fonte e licenza diverse |
| `ims-...` (uno qualsiasi della famiglia) | la famiglia con la definizione `scoperto` |

Sul cambio candidato: un giro di writer su due canary e un giro di reviewer su
altri due, **in dry-run** (senza commit ne' pull request), letti a mano contro
il brief. Se il testo regge la lettura e le eval non scendono, il cambio passa.

## 3. Annotare l'esito

In coda a questo file, una riga per giro: data, che cosa cambiava, punteggi
delle tre eval, verdetto. La versione del runtime e il modello di ogni run di
produzione stanno gia' nel diario (`claude_code_version` e `model` in
`data/pipeline/runs/`), quindi una regressione osservata dopo il fatto si
data e si attribuisce da li'.

## Esiti

| data | cambio | writer | reviewer | verifier | verdetto |
| --- | --- | --- | --- | --- | --- |
| 2026-07-27 | riga fondativa: la PR che crea metro e procedura (guardie, modelli, skills, prompt snelliti) | baseline da stabilire | baseline da stabilire | baseline da stabilire | passa, con riserva dichiarata: il metro non puo' precedere se stesso. In luogo delle eval, un giro end-to-end dispatcher -> scout senza intervento (run `scout-20260727T203950Z-6f47`, cancello verde, 5 triage motivati) e il self-test del metro. Il PRIMO giro pieno di eval fissa la baseline, e da li' in poi la regola vale intera. |
| 2026-07-28 | routing e scoperta, non giudizio: `--priority` acceso nel comando del dispatcher, scout senza tetto sulle proposte piu' `--refresh` per ri-sondare il catalogo | n/a | n/a | n/a | passa. Il cambio non tocca modello ne prompt di giudizio di writer/reviewer/verificatore, quindi le tre eval non si applicano (misurerebbero cio' che non cambia); il metro resta comunque integro (`score_eval.py --self-test` ok). La prova per un cambio di routing e' quella della riga fondativa: comportamento candidato deterministico verificato: senza `--priority` il dispatcher instrada allo scout (ordine di catena, 50 in coda), con `--priority` al reviewer (smentita pubblica aperta, priorita' 120 > soglia 100). L'uncap dello scout e' codice, coperto da `tests/unit/test_scout_sources.py` (Uncapped) e dalla suite intera. |
| 2026-07-28 | merge/meccanica, non giudizio: ogni stadio della catena passa da `checks` a `auto` (`MERGE_POLICY`), piu' la robustezza scout (retry 5xx del catalogo SDMX, `REGIONAL_HINT` riconosce `reg.`). Prosa degli agenti riallineata (scout/hunter/curator/verificatore: "merge mode is auto"). | n/a | n/a | n/a | passa. Non tocca il giudizio editoriale di writer/reviewer/verificatore ne' le rubriche: le tre eval misurerebbero cio' che non cambia. Metro integro (`score_eval.py --self-test` ok). Comportamento candidato verificato deterministicamente dalla suite: un verdetto verde di curator/scout/... ritorna `merge: auto` (`test_no_chain_stage_waits_on_the_remote_ci`, `test_a_green_curator_merges_on_the_local_gate`), `decide()` con verdetto `auto` fonde senza aspettare i check (`test_it_merges_without_looking_at_the_checks`), e il meccanismo `checks` resta testato per il giorno in cui la CI partisse sulle PR MCP. Suite intera verde (840 test). Motivo: `checks` aspettava una CI che non parte sulle PR via MCP, quindi comprava un deadlock, non un verdetto; il cancello locale (stessa suite, stesso perimetro) gira prima del merge. |
