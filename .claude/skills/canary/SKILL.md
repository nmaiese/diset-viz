---
name: canary
description: >-
  Il giro di misura obbligatorio prima di cambiare modello, prompt, skill,
  hook o permessi degli agenti della catena Divario Italia. Da caricare NEL
  MOMENTO in cui qualcuno chiede un cambio del genere, prima di toccare
  qualsiasi file: un cambio di giudizio non rompe mai un test, quindi la rete
  è questa procedura.
---

# Prima di cambiare un agente, si misura

Questa skill esiste per il triggering, non per il contenuto: il documento che
possiede il canary set, la procedura estesa e il registro degli esiti è
[`docs/CANARY.md`](../../docs/CANARY.md), e va letto, non riassunto. Quello
che deve succedere, nell'ordine:

1. **Ferma la mano.** Il cambio richiesto (modello, prompt, skill, hook,
   permessi di un agente) non si applica ancora, nemmeno "per provare": dopo
   il primo giro di Routine il nuovo comportamento è già in pagina.
2. **Il metro è integro?**

   ```bash
   python3 evals/score_eval.py --self-test
   ```

3. **Le cinque eval sul candidato**, tutte:

   ```bash
   python3 evals/run_eval.py writer
   python3 evals/run_eval.py reviewer
   python3 evals/run_eval.py verifier
   python3 evals/run_eval.py reader-editor
   python3 evals/run_eval.py admissions
   ```

   Ognuna stampa il compito: si fa girare l'agente CON IL CAMBIO CANDIDATO su
   quel compito e si misura con `score_eval.py`. Il confronto è con l'ultimo
   punteggio annotato in `docs/CANARY.md`: un punteggio che scende è un no, non
   un dettaglio.

   Erano tre in questa lista, e le altre due misurano i due giudizi più
   irreversibili della catena (chi entra nel catalogo, e se un lettore comune
   capisce). Saltarle non rendeva il canary più veloce: lo rendeva cieco su
   metà di ciò che giudica.
4. **Il giro sui canary** come `docs/CANARY.md` prescrive: l'officina su due
   indicatori del set (quelli con la definizione ingannevole), in dry-run,
   letti contro il brief, più `bin/py -m officina.lint <codice>`.
5. **Annota l'esito** nella tabella in coda a `docs/CANARY.md`, qualunque sia:
   un giro non annotato è un giro che il prossimo cambio non può usare come
   confronto.
6. Solo ora, se i numeri reggono, si applica il cambio. La regressione
   osservata DOPO si attribuisce dal diario (`model` e `claude_code_version`
   nelle righe di `data/pipeline/runs/`).
