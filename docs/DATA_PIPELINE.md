# Pipeline dati e procedura di ricontrollo

Questo documento spiega come è fatto lo strato dati e, soprattutto, **cosa va
ricontrollato e riaggiornato ogni volta che si inseriscono nuovi indicatori o
dataset**. Le categorie, i punteggi delle tematiche, i profili regionali e le
macro-aree sono tutti derivati dai dati: se aggiungi righe senza fare i controlli
qui sotto, il sito continua a funzionare ma rischi tematiche non valutate,
indicatori mal orientati o macro-aree incomplete.

## Da dove arrivano i dati

- Sorgente unica: `app/static/data/Assoluti_Regione.csv` (delimitatore `;`,
  12 colonne, 20 regioni). Generato da `scripts/update_data.py`, che scarica
  l'archivio Istat, normalizza i nomi regione e scrive il CSV.
- Le **categorie (temi)** sono la colonna `Tema` del CSV, prese verbatim da Istat.
  Non esiste un elenco di temi hard-coded: backend e frontend leggono i temi dal
  catalogo. Quindi un tema nuovo nel CSV compare da solo.
- Il **catalogo** (`app/data.py:get_catalog`) aggrega per indicatore e per tema,
  calcola completezza, anni, sparkline e aggiunge la `macro_area`.
- I **profili regionali e le tematiche valutabili** (`app/profiles.py`) sono
  calcolati **a runtime** e messi in cache (`@cache.memoize(timeout=3600)`).
  Non c'è nessun artefatto precalcolato su disco: il "ricalcolo" avviene da solo
  alla scadenza della cache o al riavvio del processo.

## Come funziona la valutazione delle tematiche

1. Solo gli indicatori **core** entrano nel punteggio: completi su tutte e 20 le
   regioni (`completeness >= 0.98`) e recenti (`year_max >= CORE_MIN_YEAR`, oggi
   2023). Vedi `profiles.is_core`.
2. Ogni indicatore core viene normalizzato in **percentile** dentro se stesso
   (stesso anno, tutte le regioni) e **orientato** in base alla direzione
   (`higher_better` / `lower_better` / `higher_worse`). Gli indicatori
   `contextual` non hanno un verso migliore/peggiore: restano visibili in modo
   descrittivo ma **non entrano nel punteggio**.
3. Il punteggio di un tema per una regione è la media degli indicatori
   direzionali di quel tema, ma solo se sono almeno `MIN_THEME_INDICATORS` (3).
   Sotto questa soglia il tema compare come "non valutabile".

La direzione di ogni indicatore viene da `app/indicator_notes.py`:
prima il dizionario curato `CURATED_DIRECTION` (per id), poi un'euristica a
parole chiave (`_direction`). **L'euristica spesso ritorna `contextual`**: i nuovi
indicatori vanno quindi quasi sempre aggiunti a mano a `CURATED_DIRECTION`.

## Macro-aree (overlay non distruttivo)

Le 26 tematiche Istat sono raggruppate in ~6 macro-aree in
`app/indicator_notes.py:MACRO_AREAS`. È un overlay: non tocca le etichette Istat,
serve solo come filtro di livello superiore in atlante e pagine regione. La mappa
è la sorgente unica: il catalogo (`macro_area` per indicatore/tema e lista
`macro_areas[]`) e i profili la leggono da qui.

Se un tema non è mappato, `macro_area_for` ritorna `"Altro"`: utile come
campanello d'allarme, ma da correggere subito aggiungendo il tema a `MACRO_AREAS`.

## Checklist quando aggiungi indicatori o dataset

1. **Schema** invariato: 12 colonne nell'ordine atteso (lo verifica
   `test_dataset_schema`). Non aggiungere/rimuovere colonne.
2. **Direzione** di ogni nuovo id: aggiungi una voce in `CURATED_DIRECTION`
   (`higher_better` / `lower_better` / `higher_worse` / lascia `contextual` se non
   c'è un verso onesto). Senza questo, l'indicatore quasi sempre resta
   `contextual` e non viene valutato.
3. **Macro-area** di ogni nuovo *tema*: mappalo in `MACRO_AREAS`. Controlla che
   nessun tema finisca in `"Altro"` (vedi diagnostica sotto).
4. **Ricalcolo**: è runtime + cache 1h. Per vederlo subito **riavvia gunicorn**
   (o aspetta la scadenza). I test girano senza cache, quindi sono sempre freschi.
5. **Frontend**: `cd frontend && npm run build && cd ..` (il catalogo cambia, la
   SPA va ricostruita).
6. **Test**: `.venv/bin/python -m unittest discover -s tests -v` (tutti verdi).
7. **Verifica tematiche**: controlla quali temi sono ora valutabili (>= 3
   indicatori core + direzionali) e quali restano descrittivi. Usa la diagnostica
   qui sotto.

## Diagnostica: temi valutabili vs descrittivi

Comando read-only per rigenerare la tabella "tema -> indicatori totali / core /
direzionali / valutabile":

```bash
.venv/bin/python - <<'PY'
from collections import defaultdict
from app.data import get_catalog
from app.profiles import is_core, SCOREABLE_DIRECTIONS, MIN_THEME_INDICATORS
tot, core, score = defaultdict(int), defaultdict(int), defaultdict(int)
for it in get_catalog()["indicators"]:
    th = it["theme"]; tot[th] += 1
    if is_core(it):
        core[th] += 1
        if (it.get("explain") or {}).get("direction") in SCOREABLE_DIRECTIONS:
            score[th] += 1
for th in sorted(tot, key=lambda t: -score[t]):
    rated = "valutabile" if score[th] >= MIN_THEME_INDICATORS else "descrittivo"
    print(f"{th:42} tot={tot[th]:>3} core={core[th]:>3} dir={score[th]:>3}  {rated}")
PY
```

Esempio di lettura: un tema con `dir=0` (come "Demografia e popolazione", i cui
indicatori 920-923 sono tutti `contextual` per scelta) resta descrittivo; un tema
con `dir>=3` viene classificato e compare nei punti di forza/debolezza regionali.

## Cosa NON cambiare

- Le 20 regioni (`REGION_ORDER`) e la mappatura nomi in `scripts/update_data.py`.
- Lo schema CSV (12 colonne, ordine).
- `/legacy` e `/legacy-reddito`.
- Gli attributi `data-key` della mappa SVG, che devono combaciare con gli slug
  regione (lo verifica `test_regions_map_data_matches_geometry`).
