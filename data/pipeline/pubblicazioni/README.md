# Il registro delle prove di pubblicazione

Un file per record, come `verifiche/`. Ogni file e' una **prova che il sito ha
servito una versione** di una pagina indicatore in un momento dato: la
transizione `fusa -> pubblicata` del modello a pratica (§8 di
[`docs/EDITORIAL_PRACTICE.md`](../../../docs/EDITORIAL_PRACTICE.md)).

Il merge non e' la pubblicazione: il repository puo' essere avanti e il sito
indietro. La prova chiude quel buco. Porta l'impronta `prosa` della versione
verificata, cosi' **scade quando il testo cambia**, esattamente come le schede di
`verifiche/`: una pubblicazione verificata resta verificata finche' il sito serve
quella versione, non per sempre.

```bash
# verifica un indicatore contro il sito e registra la prova
python3 scripts/verify_publication.py --indicator dem:NMIGRATEIN --write

# contro un'istanza locale (l'app come sito)
python3 scripts/verify_publication.py --indicator 651 --base http://127.0.0.1:5050 --write

# la ricostruzione legge le prove e porta a pubblicata gli indicatori confermati
python3 scripts/practice_timeline.py --indicator 651
```

Nome del file: `<code>__<level>__<prosa>.json` (es.
`ter-651__regione__a023f83bf666e85f.json`). Il campo `ok` dice se la firma di
contenuto (frammento del lead + anno) combaciava, `prosa` ancora la prova alla
versione.

**Il passo del sito e' acceso, quindi questa cartella si popola da sola.** La
transizione e' legata alla catena in due punti: il perimetro nel cancello
(`pipeline_gate.STAGE_PATHS["publisher"]`, con `check_publications`) e il passo del
dispatcher (`pipeline_dispatch.py --publish`, meccanico come il tick, che verifica
gli indicatori fusi contro il sito e committa qui le prove). Il comando in
`.claude/agents/dispatcher.md` passa `--publish`, quindi a ogni giro (sessione
fresca, ogni 3 ore) le prove nuove arrivano qui. Per spegnere il passo, togliere
`--publish` da quel comando.

```bash
# il passo del sito: verifica ogni indicatore fuso e committa le prove
python3 scripts/verify_publication.py --queue                     # cosa aspetta la verifica
python3 scripts/pipeline_dispatch.py --publish --publish-base https://divarioitalia.it
```
