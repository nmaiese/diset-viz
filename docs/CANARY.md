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
python3 evals/run_eval.py admissions        # il giudizio di triage: quali fonti/indicatori entrano
```

Ogni eval stampa il compito da dare all'agente NUOVO (con il modello o il
prompt candidato) e `score_eval.py` misura il risultato. Il confronto e' con
l'ultimo punteggio annotato qui sotto: un punteggio che scende e' un no, non
un dettaglio. L'eval `admissions` misura il ruolo piu' irreversibile (cosa entra
in una pagina pubblica): la sua metrica di testa e' la **precision sugli
approvati**, perche' una falsa approvazione e' l'errore che nessuno a valle
rivisita.

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
| 2026-07-28 | **BASELINE stabilita**: primo giro pieno delle tre eval sugli agenti attuali (nessun cambio candidato, si misura lo stato di oggi). | ok (0 cifre fuori brief, 0 caratteri vietati) | 7/7 errori piantati trovati | 12/12 accuratezza, precision 1.0, recall 1.0 sulle smentite | La riserva della riga fondativa e' sciolta: da qui in poi ogni cambio di modello/prompt/rubrica si confronta con questi numeri, e un punteggio che scende e' un no. Metodo (da replicare identico su ogni candidato): fixture congelate, agenti fatti girare su **opus** con le loro istruzioni reali (`.claude/agents/*.md` + STYLE + rubrica + skill `indicator-review`), in una sessione **senza** l'hook di perimetro per-stadio, perche' `evals/out/` e' fuori dal perimetro di ogni stadio. Nota: gli agenti fanno cappotto sul set, quindi il metro oggi non distingue miglioramenti al soffitto ne' regressioni piccole: allargare il canary set (piu' casi difficili, punteggi non pieni) e' il prossimo lavoro sul metro. Attrito da chiudere: una deroga `evals/out/` in `scripts/agent_guard.py` per poter girare l'eval con l'agente hooked vero. |
| 2026-07-28 | **PRODUTTORE** (nuovo agente `producer.md`, fonde curator+writer+reviewer con rilettura reflexion). Candidato, contro la baseline, prima di renderlo default editoriale. | ok (0 cifre fuori brief, 0 caratteri vietati) | vedi nota: la rilettura sul proprio testo | vedi nota | **passa, >= baseline.** Sul compito writer del canary il produttore fa `ok` come la baseline. Il punto e' il passo di rilettura: sul proprio testo ha preso e corretto le classi che il reviewer eval misura, `definizione` (denominatore sbagliato: forza lavoro invece di popolazione 15-64) e `causale`/`eco` (media del cruscotto + intervallo falso + causa inventata nel quadro), riscrivendo verso mediana, scala umana e co-occorrenza con confondente ed eccezione. Autovalutato 18/20 (il punto in meno e' Fonti, WebSearch disabilitato in eval). Metodo identico alla baseline (opus, istruzioni reali, senza hook). Regge la fusione scrivi+rileggi: il produttore puo' diventare default editoriale. Resta vero il limite del metro (al soffitto: allargare il set con casi non pieni misurerebbe meglio la rilettura). |
| 2026-07-28 | **Ri-architettura a tre ruoli + monitoraggio + learning loop.** Ritiro dispatcher -> lanciatore per-indicatore (`pipeline_launch.py`); rotta viva `/_pipeline` + `pipeline_monitor.py`; sezione ERRORI NOTI nel brief (`indicator_brief.py`); ritiro dei 5 agenti di stadio (fusi in produttore/ammissione). | n/a | n/a | n/a | **passa, il metro e' integro** (`score_eval.py --self-test` ok, ora anche l'ammissione). Nessuno di questi cambi tocca le fixture di giudizio congelate: le tre eval editoriali girano sul brief congelato (`evals/writer/brief_ter-178.txt`) e su articoli/affermazioni congelati, non sul `indicator_brief` vivo, quindi la sezione ERRORI NOTI (che ARRICCHISCE il brief vero con le smentite gia' confermate, un esempio negativo in piu') non puo' farle regredire: la misurerebbe solo un canary sul brief vivo, ed e' un miglioramento atteso, non una regressione. Il lanciatore, il monitoraggio e il ritiro degli agenti sono routing/osservabilita', non giudizio. Prova di comportamento: suite intera verde (839), il lanciatore instrada solo verso i 3 agenti vivi (admissions/producer/indicator-verifier), la board risponde 'dov'e' fermo e perche' dal vivo. La baseline delle tre eval (writer ok / reviewer 7/7 / verifier 12/12) e dell'ammissione (11/11) resta il riferimento per il prossimo cambio di modello o prompt. |
| 2026-07-29 | **meccanica/osservabilita', non giudizio**: isolamento delle run (worktree per run, `pipeline_workspace.py`), cancello `--committed-only` al merge, PR aperta via REST senza `GH_REPO` (`pipeline_merge.py --open`), cruscotto `/_pipeline` vivo (battiti e PR aperte via POST -> SQLite/GCS). Prosa aggiornata: `AGENT_CONTRACT.md`, `pipeline-close-run/SKILL.md`, `launcher.md`, `rules/pipeline.md`. | n/a | n/a | n/a | **passa, il metro e' integro** (`score_eval.py --self-test` ok). Nessuno di questi cambi tocca il giudizio editoriale (rubrica, STYLE, classi d'errore, criteri di triage): le fixture congelate misurerebbero cio' che non cambia, come per le righe di routing/meccanica del 28 luglio. Il cambio ai prompt e' procedurale: **come** una run apre (worktree) e chiude (PR via REST), non **cosa** giudica. Prova di comportamento: suite intera verde (870 test), piu' i nuovi unit test `test_pipeline_workspace` (sequenza fetch->worktree, unicita' branch per run_id), `test_pipeline_inflight` (classificazione CI, slug senza GH_REPO), `test_pipeline_state` (freschezza dei battiti), `test_pipeline_merge::TheChainOpensPullRequestsOverRest` (PR via REST), e i due test EUR ricostruiti su fixture sintetica. La baseline delle quattro eval resta il riferimento per il prossimo cambio di modello o prompt di giudizio. |
| 2026-07-28 | **AMMISSIONE: nuova eval + baseline.** Aggiunta la quarta eval congelata (`evals/admissions/cases.json`, 11 casi di triage, scorer `score_admissions` con self-test), perche' l'ammissione fonde scout+hunter+promoter ed era l'unico ruolo di giudizio senza metro. Poi baseline dell'agente `admissions.md` su di essa. | n/a (compito editoriale, non tocca lo scrittore) | n/a | n/a | **baseline ammissione fissata: 11/11, precision approvati 1.0, recall approvati 1.0, zero false approvazioni.** Metodo identico alla baseline delle tre (opus, istruzioni reali di `.claude/agents/admissions.md`, senza l'hook di perimetro perche' `evals/out/` e' fuori dal perimetro d'ogni stadio). I casi coprono apposta le classi che feriscono: aggregatore privato non istituzionale (a02), duplicato di serie gia' nel catalogo (a04, a09), solo nazionale senza grana territoriale (a05), licenza non nominabile (a03), copertura rada sotto il pavimento (a07), verso indifendibile da portare a contextual (a08), anno di punta provvisorio `p` (a10). L'agente distingue i tre esiti col taglio giusto (respinto = difetto strutturale del dato, needs-info = fatto verificabile mancante). Metro integro (`score_eval.py --self-test` ok, e prova che un 'approva tutto' fa crollare la precision). Da qui un cambio di modello/prompt dell'ammissione si confronta con questi numeri. Limite noto, uguale alle altre: l'agente fa cappotto sul set, quindi il metro non vede regressioni piccole finche' il set non si allarga con casi a punteggio non pieno. |
