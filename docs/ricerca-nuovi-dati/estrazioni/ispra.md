# ESTRAZIONE ISPRA consumo di suolo (modulo ispra_suolo, prefisso ISPRA)

## Cosa fatto
Estratti 3 indicatori dal file `lavoro/cache/consumo_suolo_full_v1.1.xlsx` (63 MB, rapporto SNPA 2025, dati 2006-2024):

1. **ISPRA_SUOLO_PERICOLO_IDRAULICO** (campo `pidrau3`): Quota aree a pericolosità idraulica già consumate (%), lower_better
2. **ISPRA_SUOLO_ALTERATO_100M** (campo `diseco6`): Territorio alterato dal consumo di suolo entro 100 m (%), lower_better
3. **ISPRA_SUOLO_NUOVO_CONSUMO** (campo `csuolo9`): Nuovo consumo di suolo in m² per ettaro, lower_better

## Copertura vera
- **Province**: 107/107 per tutti e 3 gli indicatori, 12 anni (2006, 2012, 2015-2024) = 3852 righe
- **Regioni**: 20/20 per tutti e 3 gli indicatori, 12 anni = 720 righe
- **Totale CSV**: 4572 righe

## Problemi e note
- **Ultimo anno 2024**: Il rapporto SNPA 2025 (pubblicato ottobre 2025) ha dati fino al 2024. Nessuna edizione 2026 trovata al 1/10/2026 (uscita annuale a ottobre). Dichiarato in `note` del manifest.
- **Anni 2012 e 2015**: Sono periodi pluriennali (2006-12, 2012-15), non anni singoli. Mantenuti come etichette anno 2012 e 2015.
- **Versione 2023_rev**: Esclusa per non mescolare con uscita standard 2023.
- **Trentino Alto Adige**: Nei fogli Regioni già aggregato (Bolzano + Trento ricalcolato da ISPRA su numeratori/denominatori, non media di medie). Nome armonizzato "Trentino Alto Adige" (spazio) per coerenza con `app.data.REGION_ORDER`.
- **Valori negativi csuolo9**: Presenti (es. Ancona 2021: -0,12 m²/ha) = rinaturalizzazione > nuovo consumo. Intervallo test esteso a -10..100.
- **URL file completo**: Non verificato (non compare tra i link della pagina ISPRA). Riportato in manifest come non verificato.

## Valori noti verificati (2024)
| Indicatore | Provincia alto | Provincia basso | Provincia medio | Regione alto | Regione basso | Regione medio |
|------------|----------------|-----------------|-----------------|--------------|---------------|---------------|
| pidrau3    | Trieste 58,19% | Matera 2,32%    | Cagliari 11,34% | Liguria 33,29% | Basilicata 2,62% | Lombardia 11,00% |
| diseco6    | Monza 91,67%   | Aosta 17,37%    | Forlì-Cesena 49,69% | Puglia 61,90%* | Valle d'Aosta 12,21%* | Friuli 43,40%* |
| csuolo9    | Cagliari 17,78 | Imperia 0,11    | Biella 1,94     | Lazio 4,57   | Valle d'Aosta 0,33 | Friuli 2,30 |

*Nota: gli esempi regione del rapporto ricerca usano `diseco3` (60m), non `diseco6` (100m) estratto qui. Valori diversi ma coerenti.

## Cose non verificate
- Legenda classi pericolosità idraulica (P1/P2/P3 = bassa/media/alta): non confermata su rapporto completo
- Metodo calcolo `pidrau3` = `pidrau1/(pidrau1+pidrau2)*100`: verificato su 4 province campione, non su tutte
- URL esatto file `consumo_suolo_full_v1.1.xlsx` su consumosuolo.isprambiente.it: non ritrovato

## File prodotti (committati)
- `scripts/nuovi_dati/ispra_suolo.py` — script idempotente con `--offline`
- `app/static/data/nuovi/ispra_suolo.csv` — dati normalizzati (; UTF-8, decimali con punto)
- `app/static/data/nuovi/ispra_suolo_manifest.csv` — metadati 3 indicatori
- `tests/unit/test_nuovi_ispra_suolo.py` — 11 test (schema, territori, duplicati, range, 9 valori noti) — **PASS**