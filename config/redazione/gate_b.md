# Gate B indipendente: {chiave}

Issue: {issue}
Worktree: {worktree}

Applica la sezione B di `/mnt/c/Users/Nilo/orca/specs/REDAZIONE-divario-v2.md`. Famiglia diversa dall'autore.
Valuta T/R/L/N con citazioni della bozza, anti-invenzione, rilievi localizzati, conteggio dei bloccanti, voto e
motivo. PASSA richiede voto almeno 4 e zero bloccanti. Scrivi `lavoro/{chiave}/verifica.md` (ricalcoli e
controlli) e `lavoro/{chiave}/gate-b.md` con ESATTAMENTE questi campi, ognuno all'inizio di una riga
(l'orchestratore li legge con un parser rigido):

```
# Gate B: {chiave}
Esito: PASSA oppure RISCRIVERE oppure FERMO   (solo una parola dopo i due punti)
SHA bozza: <git rev-parse HEAD al momento del giudizio>
Hash bozza: <sha256sum lavoro/{chiave}/bozza.md, 64 caratteri esadecimali, nient'altro sulla riga>
Famiglie autore/revisore: <famiglia e modello dell'autore e tuoi>
T: sì oppure no — <citazione della bozza: la tesi è sostenuta dalle prove>
R: sì oppure no — <citazione: confronto fra due territori reali che fa avanzare il racconto>
L: sì oppure no — <citazione: significato concreto per il lettore nei primi due paragrafi>
N: sì oppure no — <citazione: risultato non ovvio e controllo contrario riconoscibili>
Controllo anti-invenzione: <persone solo da fonti citate: esito>
Bloccanti: <numero intero>
Voto: <1-5> <motivo breve>
Motivo: <perché>
Rilievi localizzati: <elenco con riga e correzione, o «nessuno»>
Giri: <1 o 2>
```

Input:
{input}

Output:
{output}
