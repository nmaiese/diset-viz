# Le eval della skill nel progetto: precedenza e cancello

`evals.json` e `manifest.json` sono la suite di eval della skill
`scrittura-italiana`, copiati **invariati** dall'upstream (commit
`4987e09`, vedi
[`.claude/skills/scrittura-italiana/ATTRIBUZIONE.md`](../../.claude/skills/scrittura-italiana/ATTRIBUZIONE.md)).
Non si modificano: due suite che divergono in silenzio sono il guasto da cui
apre `CLAUDE.md`. La differenza di progetto sta **qui accanto**, non dentro il
file a monte.

## Come si girano (e perché non nella suite Python)

Il runner della skill (`run.mjs`, `activation.mjs`, ...) è **Node** e chiama il
CLI `claude`: fa girare un editor e un giudice LLM, quindi non è deterministico
e non entra in `tests/` né nella suite del progetto. Come le eval degli agenti
in `evals/`, è la **rete sotto un cambio di modello, prompt o skill** (procedura
in [`docs/CANARY.md`](../../docs/CANARY.md)), non un test da verde ripetibile.
Gli script `.mjs` non sono copiati nel repo: si eseguono dal checkout upstream.
Il metro deterministico che il progetto **aggiunge** è `tic_count.py`.

## La precedenza: gli assoluti di progetto vincono sulla skill

La skill giudica i suoi output nel registro **testo controllato**, dove
raccomanda caporali `« »`, lineette spaziate e il punto e virgola. Le sue
aspettative lo riflettono: su **34 dei 46 casi** il testo atteso o le
aspettative usano `;` o `« »`, e alcuni casi **premiano esplicitamente** la
punteggiatura che il progetto vieta. I più netti:

| caso | cosa premia l'upstream | verdetto di progetto |
|---|---|---|
| 1 | conservare il `;` dell'input ("scelte legittime") | il `;` va sciolto: due frasi o una virgola |
| 4 | non convertire `...` (chat informale) | fuori scope: il progetto scrive testo editoriale, non chat |
| 18, 23, 28, 31, 36, 40, 41, 42 | caporali `« »` e/o `;` nel testo atteso | virgolette dritte `" '`, niente `;` |
| 19, 21, 27, 30, 45 | normalizzare verso i caporali `« »` | virgolette dritte `" '` |
| 38, 43 | normalizzazione tipografica verso lo stile editoriale (caporali, lineette) | assoluti di progetto: niente `— – ; …`, virgolette dritte |
| 31 | ammette `…` (puntini come carattere) | tre punti normali `...` |

Questi casi restano nella suite **come sono**, perché misurano la skill sul suo
terreno. Ma quando il bersaglio è la **prosa di Divario Italia**, il verdetto
della colonna di destra vince. La ragione, e la lista completa degli assoluti,
stanno in [`content/STYLE.md`](../../content/STYLE.md).

## Il cancello deterministico (che il giudice LLM non può scavalcare)

Perché la precedenza non resti un buon proposito, ogni output prodotto con la
skill su prosa di progetto passa un controllo **deterministico** che nessun
giudice LLM può annullare:

```bash
python3 evals/scrittura-italiana/tic_count.py <file>   # campo "vietati" deve essere []
```

`tic_count.py` tratta `— – ; …` non come un tic da pesare ma come un **cancello**:
il campo `vietati` deve essere vuoto. È lo stesso perimetro di
`evals/score_eval.py` (`BANNED`) e delle guardie di `tests/`. Un output che
piace al giudice della skill ma contiene un `;` **non passa**: gli assoluti di
progetto sono un vincolo di codice, non un'opinione editoriale.
