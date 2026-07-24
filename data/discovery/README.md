# Coda di discovery (staging revisionabile)

Questa cartella è la "discarica di sistema" davanti alla pipeline dati. Un
**agente cacciatore** schedulato scrive qui i candidati che trova nelle fonti
istituzionali, senza mai toccare i dati live. Un umano (o l'agente integratore)
li revisiona in una pull request prima che possano entrare nel sito.

## File

- **`candidates.csv`** — la coda, versionata in git. Una riga per indicatore
  candidato. Colonne definite in `scripts/discovery.py:CANDIDATE_COLUMNS`.
- **`fixtures/eurostat/*.json`** — risposte JSON-stat Eurostat reali, bounded,
  usate per le run offline e i test. La cache grezza live sta in
  `data/eurostat_cache/` (gitignorata).

## Ciclo di vita di un candidato (`triage_status`)

1. `new` — appena scoperto dal cacciatore. Default.
2. `approved` — un umano lo ha validato in PR: solo questi vengono promossi.
3. `rejected` — scartato (es. duplica un BES, licenza incerta, copertura bassa).
4. `needs-info` — serve un controllo manuale prima di decidere.
5. `promoted` — già portato nel layer esterno da `promote_candidates.py`.

Il cacciatore **non sovrascrive** le decisioni umane: su una nuova run
aggiorna solo i campi dati (anno, copertura, punteggio) di un candidato già
revisionato, lasciando intatti `triage_status` e `triage_notes`.

## Comandi

```bash
# cacciatore (watchlist), offline sui fixture committati
python3 scripts/discover_candidates.py --source eurostat_regional --offline
# cacciatore live (cache-first)
python3 scripts/discover_candidates.py --source eurostat_regional
# solo ranking, senza scrivere la coda
python3 scripts/discover_candidates.py --source eurostat_regional --offline --dry-run

# integratore: promuove SOLO i candidati con triage_status=approved
python3 scripts/promote_candidates.py --offline --dry-run
python3 scripts/promote_candidates.py --offline
```

Vedi [`docs/DISCOVERY_PIPELINE.md`](../../docs/DISCOVERY_PIPELINE.md) per
l'architettura completa e il contratto dell'agente schedulato.
