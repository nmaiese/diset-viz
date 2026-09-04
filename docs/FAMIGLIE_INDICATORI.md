# Famiglie di indicatori: dimensioni e livelli

Priorità decisa il 4 settembre 2026 sera (Quadro di `redazione-ai`, Decisioni;
`docs/RIPARTENZA.md` §4.3 e §5). Questo documento raccoglie la ricerca già
fatta, così una sessione nuova non la rifà da capo: che cosa esiste oggi, che
cosa manca, dove si tocca. Non è ancora un disegno definitivo: i punti aperti
sono segnati come tali alla fine.

## Il problema

Molti indicatori del catalogo sono la stessa misura vista da una dimensione
diversa (totale, maschi, femmine, a volte una fascia d'età) o da un livello
territoriale diverso (regione, provincia). Oggi ognuno è una pagina e un
articolo separati, scritti uno alla volta, senza che la pipeline sappia che
sono la stessa cosa.

## Due situazioni diverse, verificate sul codice

### 1. Il catalogo storico (`app/static/data/Assoluti_Regione.csv`)

Prodotto da `scripts/update_data.py`, che scarica lo ZIP statico Istat
`Archivio_unico_indicatori_regionali.zip` (BDTPS) e converte ogni riga con
`convert_row` (`scripts/update_data.py:106-138`). Non è una query SDMX con
dimensioni: è un CSV già piatto. Istat stessa ha già diviso le variabili in
più `COD_INDICATORE` distinti, con la dimensione scritta nel titolo, non in
un campo strutturato.

Esempi reali verificati nel CSV:
- id 345 "Tasso di occupazione 20-64 anni" (totale), 346 (maschi), 347
  (femmine): tripletta pulita, id adiacenti.
- id 339 "Tasso di istruzione terziaria 30-34 anni" (totale), 340 (maschi),
  342 (femmine): quasi adiacenti (341 non usato).
- id 14 "Tasso di occupazione over 54" (totale) vs 181 (maschi) / 182
  (femmine): stessa misura, id lontani. Smentisce qualunque convenzione di
  adiacenza numerica.
- id 203 "Tasso di attività totale (femmine)" vs 213 (maschi): 10 di distanza.
- id 175/176 "Tasso di disoccupazione" (maschi/femmine): adiacenti, nessun
  "totale" trovato vicino.

Circa 64 righe (32 coppie o triplette) nel catalogo rispondono a un pattern
`maschi`/`femmine`/`totale` nel testo del titolo.

**Conseguenza**: qui la dimensione va letta dal testo del titolo (parser
euristico), non recuperata da una fonte più ricca. Non c'è nulla "nascosto"
da riscoprire: Istat non la struttura in questo archivio.

### 2. Le pipeline SDMX (provincia, BES, scoperta di nuovi indicatori)

Qui il sistema sa già che una serie ha dimensioni. `config/istat_series.yaml`
ha `dimension_order` (es. `[FREQ, REF_AREA, SESSO, ETA1, DATA_TYPE]`) e
`dimension_values` che oggi fissa sempre il codice "totale" (`SESSO=9`,
`ETA1=99`). `scripts/istat_regional_source.py:14-21` lo dice esplicitamente:
la maggior parte dei dataflow Istat si scompone anche per sesso, fascia d'età,
tipo di nucleo, e il modulo "rifiuta di costruire una chiave per una
dimensione senza un valore noto, invece di usare un wildcard".

Le tabelle di codice sono **già committate e inutilizzate**:
- `data/provincia/codelist_CL_SEXISTAT1.csv`: codici 1 (maschi), 2 (femmine),
  9 (totale), M/F/T.
- `data/provincia/codelist_CL_ITTER107.csv`: gerarchia territoriale con
  colonna `parent`, regione e provincia nello stesso file.

`tests/integration/test_discovery.py:526-531` mostra righe SDMX grezze che
contengono già `SESSO=1/2/9` per la stessa regione e lo stesso anno: la
dimensionalità piena esiste a monte ed è filtrata al momento di costruire la
chiave di query (`scripts/istat_regional_source.py:185-218`), non scartata
dopo.

La pipeline provinciale è già separata e documentata in
`docs/PROVINCE_PIPELINE.md`: scrive `app/static/data/Assoluti_Provincia.csv`,
non tocca `Assoluti_Regione.csv` né `app/data.py`, è caricata da
`app/bes_data.py`.

**Conseguenza**: qui prendere maschi/femmine o il livello provincia è
cambiare la chiave della query SDMX già scritta (`dimension_values`), non
costruire un'infrastruttura nuova.

## Concetti già esistenti, e perché non bastano

- **"Famiglia" oggi** (`app/indicator_universe.py`) è la fonte dati (`ter`,
  `bes`, `eur`, `multiscopo`), non la misura condivisa. Nessuna relazione con
  quello che serve qui.
- **"Parenti"/siblings** (`app/indicator_view.py:542-576`,
  `_theme_neighbours`/`_theme_siblings`) sono legati per tema Istat, non per
  misura: nella stessa lista finiscono indicatori senza nulla in comune oltre
  al sotto-tema.
- Nessun concetto "raccolta" esiste nel codice (cercato, zero risultati reali
  al di fuori di "raccolta differenziata" come nome di un indicatore e
  "raccolta dati" in `docs/tracking_spec.md`, entrambi non pertinenti).

Serve un terzo concetto, "famiglia di misura", distinto dagli altri due.

## Dove si tocca

- Dati: `app/data.py`, `scripts/update_data.py`, `config/istat_series.yaml`,
  `scripts/istat_regional_source.py`, i codelist in `data/provincia/`.
- Routing e vista: `app/views.py:1145` (rotta `/indicatore/<slug>/<id>`),
  `app/indicator_view.py` (`build_indicator_view`, i "parenti").
- Contenuto: `content/indicators/<id>.json`, uno per id oggi, sezioni con
  `role` in `{definizione, quadro, dinamica, limiti}`.
- Frontend: il componente che rende la pagina indicatore (in `frontend/src/`).
- Redazione (`nmaiese/redazione-ai`): `motore/dossier.py`, `motore/brief.py`,
  `motore/verifica.py`, `motore/coda.py`, `motore/pubblica.py`.

## I quattro passi (RIPARTENZA.md §4.3)

a. Mappare le famiglie: parser euristico sui titoli per il catalogo storico
   (file curato, sul modello di `config/theme_categories.csv`), lettura
   diretta da `config/istat_series.yaml` per le serie SDMX.
b. Estendere la raccolta SDMX alle dimensioni già note e al livello provincia,
   riusando i codelist già committati.
c. Ridisegnare la pagina indicatore: una famiglia, un selettore di dimensione
   e di livello, redirect dagli id vecchi.
d. Ridisegnare `dossier`/`brief`/`verifica`/`pubblica` della redazione per un
   pezzo che tratta una famiglia intera.

Non blocca la Settimana 2 in corso: i pezzi scritti ora restano con il
modello attuale, si riscrivono quando la pagina di famiglia è pronta.

## Punti aperti, da decidere nel passo (a)

Non ancora risolti, non ancora decisi: la prossima sessione che lavora sul
passo (a) li affronta prima di scrivere codice.

1. **Affidabilità del parser euristico**: quanti falsi positivi/negativi dà
   un regex su "maschi"/"femmine"/"totale" nel titolo, su 634 indicatori? Va
   verificato con un conteggio reale prima di fidarsene, non assunto.
2. **File generato o curato a mano?** Come `config/theme_categories.csv`
   (curato) o rigenerato a ogni aggiornamento dati (automatico, poi rivisto)?
   I titoli cambiano raramente: probabile che generato-poi-rivisto sia giusto,
   ma va deciso, non assunto.
3. **Schema del contenuto**: un file per famiglia in `content/indicators/`
   (quale slug/id lo rappresenta?) o un nuovo `content/famiglie/<chiave>.json`
   separato dai file per id, che restano per compatibilità? Tocca anche gli
   URL canonici e i redirect dagli id vecchi.
4. **Ambito del pilota**: quale famiglia usare come prima prova end-to-end?
   Un candidato con dati completi su tutte le dimensioni note e già con
   traffico reale (es. la tripletta 345/346/347, occupazione 20-64, che è fra
   le pagine con più impression).
