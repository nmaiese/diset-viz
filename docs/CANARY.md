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
| _(nessun giro ancora annotato)_ | | | | | |
