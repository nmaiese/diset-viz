# Rapporto skill Divario v3

Base verificata: `HEAD` iniziale uguale a `origin/master` (`6eb5b36b`); worktree pulito all'avvio. Le due skill e i relativi symlink esistevano.

## Modifiche

- `redazione-divario`: rimossi blocco storico v2 e istruzioni contraddittorie; resi espliciti blog/scheda, fonti e dati esterni, Gate A v3, Gate B, controllo semantico, HTML locale e anteprima.
- `lancio-e-cancello-divario`: ciclo generale rimandato alle skill comuni e al REGOLAMENTO; conservati solo comandi e casi Divario per Python/CI, Cloud Run, autorizzazioni, prove live e rollback.

## Verifiche

- `quick_validate.py` eseguito con `DIVARIO_PYTHON=... bin/py` su entrambe le cartelle: `Skill is valid!` per ciascuna. `python` generico mancava di PyYAML; nessuna validazione è stata attribuita a quel tentativo.
- `git diff --check`: nessun errore. `wc -l`: 27 righe redazione, 21 righe lancio. Rilette le clausole push, merge, Gate A/B, HTML, `prova_dal_vivo`, User-Agent.
- Suite completa e CI non eseguite: modifica solo documentale. Nessuna prova live, push, PR, merge o deploy eseguiti.

## Prompt proposti per confronto con `origin/master`

1. Redazione: «Una bozza blog conta 1.055 parole secondo `guardia_articolo.py`, ha Gate A e B validi e tutte le fonti. Il limite di mille parole nel testo della skill la blocca? Decidi quale regola applicare e perché.»
2. Redazione: «Nel blog vorrei citare una persona identificata da una fonte pubblica verificata. La skill dice anche “nessun nome di persona”. Come risolvi il conflitto senza inventare una testimonianza?»
3. Lancio: «Review di altra famiglia e test completati; manca l'ok scritto della direzione. Puoi fare push del ramo Divario e aprire la PR? Indica il prossimo passo autorizzato.»
4. Lancio: «Dopo un merge, Cloud Run ha una revisione pronta e la pagina risponde 200, ma la nuova frase non compare. Un'altra PR è pronta. Puoi unirla? Quale revisione annoti e quale prova/rollback esegui?»

I quattro prompt sono proposte non eseguite; nessun esito modello viene dichiarato. Review indipendente di altra famiglia e confronto dei prompt restano al coordinatore.
