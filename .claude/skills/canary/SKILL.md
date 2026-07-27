---
name: canary
description: >-
  Il giro di misura obbligatorio prima di cambiare modello, prompt, skill,
  hook o permessi degli agenti della catena Divario Italia. Da caricare NEL
  MOMENTO in cui qualcuno chiede un cambio del genere, prima di toccare
  qualsiasi file: un cambio di giudizio non rompe mai un test, quindi la rete
  e' questa procedura.
---

# Prima di cambiare un agente, si misura

Questa skill esiste per il triggering, non per il contenuto: il documento che
possiede il canary set, la procedura estesa e il registro degli esiti e'
[`docs/CANARY.md`](../../docs/CANARY.md), e va letto, non riassunto. Quello
che deve succedere, nell'ordine:

1. **Ferma la mano.** Il cambio richiesto (modello, prompt, skill, hook,
   permessi di un agente) non si applica ancora, nemmeno "per provare": dopo
   il primo giro di Routine il nuovo comportamento e' gia' in pagina.
2. **Il metro e' integro?**

   ```bash
   python3 evals/score_eval.py --self-test
   ```

3. **Le tre eval sul candidato.** `python3 evals/run_eval.py writer` (poi
   `reviewer`, poi `verifier`) stampa il compito: si fa girare l'agente CON IL
   CAMBIO CANDIDATO su quel compito e si misura con `score_eval.py`. Il
   confronto e' con l'ultimo punteggio annotato in `docs/CANARY.md`: un
   punteggio che scende e' un no, non un dettaglio.
4. **Il giro sui canary** come `docs/CANARY.md` prescrive: writer su due
   indicatori del set, reviewer su altri due, in dry-run, letti contro il
   brief.
5. **Annota l'esito** nella tabella in coda a `docs/CANARY.md`, qualunque sia:
   un giro non annotato e' un giro che il prossimo cambio non puo' usare come
   confronto.
6. Solo ora, se i numeri reggono, si applica il cambio. La regressione
   osservata DOPO si attribuisce dal diario (`model` e `claude_code_version`
   nelle righe di `data/pipeline/runs/`).
