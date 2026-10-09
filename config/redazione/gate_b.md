# Gate B indipendente: {chiave}

Issue: {issue}
Worktree: {worktree}

Applica il Gate B v4 di `/mnt/c/Users/Nilo/orca/specs/REDAZIONE-divario-v4.md` (§4). Famiglia diversa
dall'autore. Valuta T/R/L/N nei significati v4, con citazioni della bozza e righe del registro del brief;
i criteri T includono ogni frase forte (cifra, confronto, graduatoria, direzione, causa): per ciascuna cerca
nel registro del brief affermazione corrispondente, fonte, ambito e periodo, livello di descrizione,
associazione o spiegazione documentata e dato o calcolo che la sostiene. Per spiegazioni attribuite
controlla prova specifica nella fonte; lessico G8 e URL da soli non provano causalità. Se registro manca,
è incompleto o non corrisponde alle frasi forti, scrivi FERMO con T: no e rilievi localizzati.
I criteri di pubblicazione della norma e le specifiche delle figure sono bloccanti. PASSA richiede T, R, L, N
tutti sì, voto almeno 4 e zero bloccanti; massimo due giri. Scrivi `lavoro/{chiave}/verifica.md` (ricalcoli e
controlli) e `lavoro/{chiave}/gate-b.md` con ESATTAMENTE questi campi, ognuno all'inizio di una riga
(l'orchestratore li legge con un parser rigido):

```
# Gate B: {chiave}
Contratto: v4
Esito: PASSA oppure RISCRIVERE oppure FERMO   (solo una parola dopo i due punti)
SHA bozza: <git rev-parse HEAD al momento del giudizio>
Hash bozza: <sha256sum lavoro/{chiave}/bozza.md, 64 caratteri esadecimali, nient'altro sulla riga>
Famiglie autore/revisore: <famiglia e modello dell'autore e tuoi>
T: sì oppure no — <citazione e riga del registro: ogni frase forte ha dato e fonte>
R: sì oppure no — <citazione: confronti compatibili o differenze dichiarate, contrario onesto>
L: sì oppure no — <citazione: misura e limite chiari prima del primo grafico>
N: sì oppure no — <citazione: nessun falso primato, conclusione commisurata alle prove>
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
