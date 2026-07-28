# Lo store delle pratiche editoriali

Un file per record, come `runs/` e `verifiche/`. Ogni file e' una pratica
editoriale (un ciclo di un indicatore), con la sua identita' dentro il campo
`practice_id`. Il modello e il vocabolario stanno in
[`docs/EDITORIAL_PRACTICE.md`](../../../docs/EDITORIAL_PRACTICE.md).

**In modalita' di controllo (Fase B/C) questa cartella e' vuota nel repo, ed e'
voluto.** I record si ricostruiscono dagli artefatti committati a comando, non si
committano come istantanea: una istantanea derivata invecchia sotto il flusso e
diventa il `analyst_notes.json` di turno, un file che qualcuno scrive e nessuno
rilegge. La verita' di fondo restano gli artefatti (candidati, curatela,
articoli, verifiche, run), il record di pratica e' la loro proiezione, sempre
riconciliabile.

```bash
# ricostruisci e guarda la storia per indicatore (read-only)
python3 scripts/practice_timeline.py
python3 scripts/practice_timeline.py --indicator dem:NMIGRATEIN

# materializza i record qui dentro (stato dichiarato)
python3 scripts/practice_timeline.py --write

# riconcilia il dichiarato con gli artefatti (esce !=0 se divergono)
python3 scripts/practice_timeline.py --check
```

Rendere questi record autorevoli al posto dello stato dedotto e' la Fase F, e non
va fatta prima del confronto misurabile che il mandato richiede.
