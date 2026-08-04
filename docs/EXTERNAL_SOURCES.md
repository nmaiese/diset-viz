# Fonti esterne e aggiornamenti 2025/2026

Le fonti verticali sono configurate in `config/external_sources.yaml` e
normalizzate in un dataset separato. Non modificano lo schema di
`Assoluti_Regione.csv` o `Assoluti_Provincia.csv`.

## Dataset normalizzato

Output: `app/static/data/external/normalized_external_indicators.csv`.

Campi principali: fonte, dataset sorgente, id sorgente, id target, territorio,
anno, valore, unità, categoria qualità della vita, direzione, compatibilità della
definizione, eleggibilità per atlante/profili/scoring, copertura, data di
recupero, URL e licenza.

Valori ammessi per `definition_match`:

- `exact`: può sostituire una serie esistente solo se coincidono anche unità,
  territorio, popolazione e frequenza.
- `compatible`: utile per atlante/profili, richiede revisione manuale.
- `proxy`: nuovo indicatore, mai sostitutivo.
- `different`: descrittivo.

## Fonti registrate

- `istat_bes_regioni`: appendice statistica del BES nazionale. Parser promosso:
  145 indicatori regionali, di cui 67 al 2025. È la fonte della classifica
  regionale e non sostituisce il BES dei Territori provinciale.
- `istat_lavoro`: Rilevazione sulle forze di lavoro, regioni e province. Stato:
  parser locale promosso per le righe regionali 2025 presenti nell'archivio
  BDTPS aggiornato.
- `istat_demografia`: Indicatori demografici Istat. Stato: parser promosso per
  righe regionali 2025/2026 già presenti nell'atlas.
- `invalsi`: rilevazioni nazionali 2025 e dispersione implicita. Stato: fonte
  registrata, richiede verifica di grado, soglia e universo prima di integrare.
- `movimprese`: InfoCamere/Unioncamere. Stato: fonte registrata, da usare solo
  con indicatori relativi o per 1.000 abitanti/imprese. Dati assoluti descrittivi.
- `istat_turismo`: movimento clienti negli esercizi ricettivi. Stato:
  registrata, prevalentemente contestuale.
- `terna`: statistiche elettriche. Stato: registrata. Non sostituisce il BES
  rinnovabili finché il denominatore non coincide.
- `infratel`: mappature reti fisse e Piano Italia a 1 Giga. Stato: registrata,
  richiede normalizzazione civico -> comune -> provincia -> regione.

## Comandi

```bash
.venv/bin/python scripts/discover_external_sources.py
.venv/bin/python scripts/fetch_external_data.py --source istat_lavoro --year 2025 --offline
.venv/bin/python scripts/build_external_dataset.py --source all --year 2025
.venv/bin/python scripts/audit_external_indicators.py
```

`fetch_external_data.py` è cache-first e idempotente. Finché una fonte non ha un
parser promosso, scrive solo un marker di fetch e non finge di avere scaricato
dati.

## Uso nello scoring

Il motore BES resta la fonte principale dello scoring. Le serie esterne
promosse entrano tramite `app/quality_life_selection.py` solo dopo le guardie di
freschezza, copertura e direzione curata. Qualunque sostituzione di una serie BES
deve avere `definition_match=exact`, copertura almeno 95% e un test comparativo
di stabilità dello scoring.

Per la qualità della vita regionale il motore legge direttamente il dataset BES
nazionale separato. Qui la soglia operativa è anno almeno 2025, copertura almeno
80% e direzione esplicitamente revisionata. Le serie contestuali non entrano nel
punteggio ma restano disponibili nelle schede.
