# Le eval degli agenti

La suite in `tests/` prova il codice deterministico della catena: cancello,
merge, code, diario. **Niente li' prova il giudizio degli agenti**: che lo
scrittore non inventi cifre, che il revisore trovi un errore piantato, che il
verificatore distingua una smentita da un non verificabile. Queste eval
chiudono quel buco, e sono la rete sotto ogni cambio di modello, di prompt, di
rubrica o di hook (la procedura completa e' [`docs/CANARY.md`](../docs/CANARY.md)).

Non stanno in `tests/` di proposito: fanno girare un agente, quindi non sono
deterministiche e non appartengono a una suite che deve dare lo stesso verde
due volte di fila. Deterministico e' solo il metro.

## Come si usa

```bash
python3 evals/run_eval.py writer      # prepara le fixture e stampa il compito
# ... si fa girare l'agente sul compito stampato ...
python3 evals/score_eval.py writer evals/out/writer/article.json
python3 evals/score_eval.py --self-test    # il metro provato sul metro (in CI-spirito: sempre verde)
```

Quattro eval, una per ogni ruolo che esercita giudizio, non codice:

| eval | fixture | che cosa misura |
| --- | --- | --- |
| `writer` | il brief congelato di ter-178 | nessuna cifra fuori dal brief, niente caratteri vietati |
| `reviewer` | due articoli con 7 errori piantati (`reviewer/expected.json`) | quanti errori spariscono dopo la revisione, per classe |
| `verifier` | 12 affermazioni etichettate (`verifier/claims.json`) | accuratezza, e precision/recall sulle smentite |
| `admissions` | 11 casi di triage etichettati (`admissions/cases.json`) | accuratezza, e precision/recall sugli approvati (la falsa approvazione e' l'errore irreversibile) |

## Le regole che tengono in piedi la misura

- **Tutto si giudica contro il brief congelato** (`writer/brief_ter-178.txt`),
  mai contro i dati vivi: e' cio' che rende confrontabile il punteggio di oggi
  con quello dopo un cambio di modello. Quando i dati veri di ter-178 si
  muovono, le fixture restano giuste per costruzione.
- **Gli errori piantati sono uno per classe** della skill `indicator-review`:
  media semplice spacciata per dato nazionale, definizione col denominatore
  sbagliato, universale falso, causale inventata, claim europeo senza fonte,
  cifra alterata, falso "piu' che dimezzato".
- **I casi di ammissione sono autosufficienti**: ogni caso porta scritti dentro
  l'istituzione, la licenza, il dettaglio territoriale, la cadenza, l'additivita'
  e (per i candidati) copertura e verso, e si giudica contro QUELLA descrizione,
  mai contro il catalogo vivo o il web. La licenza e' quella scritta nel caso,
  non una da aprire con WebFetch, cosi' l'esito resta ripetibile.
- **`evals/out/` e' usa e getta** e non si committa. Le fixture invece sono
  congelate: cambiarle significa cambiare il metro, e va fatto apposta, mai di
  passaggio.
- Il punteggio del reviewer conta le **sopravvivenze** (il pattern della frase
  sbagliata ancora presente), non la qualita' della riscrittura: quella resta
  una lettura umana.
