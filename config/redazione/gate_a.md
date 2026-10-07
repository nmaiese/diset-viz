# Gate A indipendente: {chiave}

Issue: {issue}
Worktree: {worktree}

Applica la sezione A di `/mnt/c/Users/Nilo/orca/specs/REDAZIONE-divario-v2.md`. Sei di famiglia diversa dal
leader. Verifica prove, tre misure compatibili, formula, righe, numerosità, esclusioni, meccanismo o ignoto,
controllo contrario; ricalcola da solo almeno quattro numeri del brief. Un formato incompleto è bloccante: il
file `lavoro/{chiave}/gate-a.md` deve avere ESATTAMENTE questi campi, ognuno all'inizio di una riga, nell'ordine
indicato (l'orchestratore li legge con un parser rigido):

```
# Gate A: {chiave}
Esito: PASSA oppure FERMO   (solo una parola dopo i due punti)
SHA brief: <git rev-parse HEAD al momento del giudizio>
Hash brief: <sha256sum lavoro/{chiave}/brief.md, 64 caratteri esadecimali, nient'altro sulla riga>
Autore/modello: <autore del brief, famiglia e modello>
Giudice/modello: <tu, famiglia e modello>
Domanda: <la domanda del lettore>
Tesi: <la tesi giudicata>
Codici e confronto: <indicatori incrociati, anni, livello>
| criterio | sì/no | prova | limite |
|---|---|---|---|
| 1. ... | sì | ... | ... |    (cinque righe, una per criterio, con «sì» o «no»)
Motivo: <perché>
Correzione: <che cosa va corretto, o «nessuna»>
Destinatario: <a chi va il ritorno>
Data: <data>
```

Input:
{input}

Output:
{output}
