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

**In modalita' di controllo (Fase D pilota) questa cartella e' vuota nel repo.**
Le prove vere si scrivono contro `divarioitalia.it` dopo un deploy, e legare la
transizione a uno stadio della catena (con il suo perimetro nel cancello) e' la
Fase F, non ancora fatta.
