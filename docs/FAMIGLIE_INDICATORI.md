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

## Tre situazioni diverse, verificate sul codice

(Erano due fino al 4 settembre sera; il 4 settembre notte l'audit delle
fonti già scaricate ne ha trovata una terza, BES, sezione 3 sotto.)

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

**Aggiornamento del 4 settembre notte, numero reale contato, non stimato**
(`Assoluti_Regione.csv` ha 393 indicatori distinti, non 634: quello è
l'universo intero con BES/multiscopo/esterni, vedi sezione 3): **30
famiglie, 89 indicatori coinvolti** (29 triplette totale/maschi/femmine più
una coppia genuina senza terzo membro, verificata a mano ("Tasso di
attività totale della popolazione", id 203/213). 14 delle 43 righe "totale"
attese sono implicite: un titolo senza suffisso che coincide con la base di
una famiglia già identificata da maschi/femmine (Istat non ripete
"(totale)" quando il titolo di partenza è già il totale); un parser che
cerca solo `(totale)` esplicito ne perderebbe un terzo. Zero falsi positivi:
ogni famiglia ha `UDM` e `Tema` coerenti fra i membri, e titoli con
"totale"/"maschile"/"femminile" a metà frase ("Tasso di attività totale
della popolazione", "Differenza tra tasso di occupazione maschile e
femminile", "Imprenditorialità femminile") sono misure diverse, escluse
correttamente da un parser a suffisso di coda.

**Non serve nemmeno il parser**: il CSV Istat ha 21 colonne, `convert_row`
ne legge 10. Fra le 11 mai lette, `DESCRIZIONE_ASSE_QCS` contiene il valore
letterale `"Asse VII - Articolazione di genere."`, che marca ufficialmente
58 indicatori (su 377 nel sottoinsieme regionale) come scomposti per
genere. Incrociato con il regex sui titoli: **combaciano al 100%, zero
discrepanze**. Il campo esiste già nel dato scaricato: per il catalogo
storico si può leggere `DESCRIZIONE_ASSE_QCS` invece di (o come conferma
di) un parser sul titolo. Un'altra colonna mai letta, `DESCRIZIONE_TEMA2`,
è una seconda classificazione tematica (11 valori: Città, Dinamiche
settoriali, Energia, Inclusione sociale, Internazionalizzazione, Istruzione
e formazione, Legalità e sicurezza, Pubblica Amministrazione, Qualità
dell'aria, Ricerca ed innovazione, Turismo), non è la dimensione di questo
documento, ma è un asse aggiuntivo mai sfruttato.

Il filtro per territorio (`SUPPORTED_REGIONS`) scarta anche 85.821 righe su
188.631 non regionali: `Italia` (5.126 righe), le macro-aree
(Nord/Sud/Centro/Isole/Nord-ovest/Nord-est/Centro-Nord/Mezzogiorno) e le tre
categorie di sviluppo UE. Il campo `Benchmark` dello schema di output esiste
già ma è sempre vuoto: la riga Italia per lo stesso indicatore/anno è il
candidato naturale per popolarlo (confronto regione-vs-Italia in un pezzo),
non ancora fatto.

Verifica riproducibile con `scripts/audit_famiglie_fonti.py` (riscarica il
CSV Istat e ristampa questi numeri) e, per le 30 famiglie in dettaglio,
`analisi/famiglie_conta.py` in `nmaiese/redazione-ai`.

**Conseguenza**: qui la dimensione va letta dal testo del titolo (parser
euristico) solo come ripiego. La fonte ha già un campo ufficiale
(`DESCRIZIONE_ASSE_QCS`) che la porta strutturata: non c'è bisogno di
inferirla dal titolo, va solo letta.

### 2. Le pipeline SDMX (provincia, scoperta di nuovi indicatori)

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

### 3. BES (`app/static/data/Assoluti_BES_Regione.csv`)

Trovata il 4 settembre notte, in un audit delle fonti già scaricate per
verificare che non si lasciasse indietro niente ("possiamo controllare che
le fonti dati che abbiamo già acquisito non avevano altri dati come questi
che potevamo usare?", Nello). Una terza situazione, diversa dalle prime due:
non un CSV piatto con la dimensione nel titolo (1), né una query SDMX a
chiave fissa (2), ma un file Excel già strutturato per dimensione,
**filtrato dopo il download**.

Lo ZIP Istat scaricato da `scripts/update_bes_regions.py`
(`APPENDICE-STATISTICA-2.zip`) contiene **cinque file Excel**; il codice ne
apre **uno solo**, `indicatori_regione_sesso.xlsx`:

- `indicatori_regione_sesso.xlsx`: usato, ma solo in parte, sotto
- `indicatori_eta_sesso.xlsx`: sesso per fascia d'età, mai aperto
- `indicatori_titolo_di_studio.xlsx`: sesso/età/titolo di studio, mai aperto
- `indicatori_titolo_di_studio_ripartizione.xlsx`: come sopra con
  ripartizione territoriale (macro-aree, non le 20 regioni), mai aperto
- `Metadati.xlsx`: definizioni testuali dei 153 indicatori, mai aperto

Anche nel file usato la colonna `SESSO` è **già strutturata**
(`Maschi`/`Femmine`/`Totale`, non testo nel titolo), e
`scripts/update_bes_regions.py:151` tiene solo le righe `Totale`:

```python
if str(values[positions["SESSO"]] or "").strip() != "Totale":
    continue
```

Verificato scaricando di nuovo lo ZIP: 8.479 righe nel foglio, 4.359 Totale
+ 2.060 Maschi + 2.060 Femmine. **84 indicatori hanno già oggi una
tripletta regionale completa Totale/Maschi/Femmine**, scartata a ogni
aggiornamento (4.120 righe). Gli altri 69 indicatori del file sono
Totale-only anche nella fonte: niente da recuperare per quelli. Stesso
filtro territoriale delle altre due fonti: il file ha 30 territori (le 20
regioni più Italia e le macro-aree), ne teniamo 20.

Verifica riproducibile con `scripts/audit_famiglie_fonti.py`.

**Conseguenza**: qui non serve né un parser sul titolo né cambiare una
chiave di query SDMX. La dimensione è già una colonna nel file che
scarichiamo: va solo smesso di scartarla in `parse_archive`
(`scripts/update_bes_regions.py:131-213`). È la fonte più economica delle
tre per una famiglia pilota: 84 famiglie pronte, più del triplo delle 30
del catalogo storico, zero euristica.

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

- Dati: `app/data.py`, `scripts/update_data.py`, `scripts/update_bes_regions.py`,
  `config/istat_series.yaml`, `scripts/istat_regional_source.py`, i codelist
  in `data/provincia/`.
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

1. **Affidabilità del parser euristico, risolto il 4 settembre notte**: il
   regex sui titoli per il catalogo storico combacia al 100% (0 falsi
   positivi, 0 falsi negativi, su 377 indicatori) con il campo ufficiale
   Istat `DESCRIZIONE_ASSE_QCS = "Asse VII - Articolazione di genere."`,
   presente nel CSV scaricato e mai letto finora (sezione 1). Non è più un
   punto aperto per il catalogo storico: si usa il campo ufficiale, il regex
   resta un controllo di coerenza. Per BES (sezione 3) non serve nemmeno
   quello: la dimensione è già una colonna `SESSO`. Resta aperto solo per
   `indicatori_eta_sesso.xlsx` e i due file titolo di studio del BES, non
   ancora guardati in dettaglio, e per quando si estenderà al livello
   provincia.
2. **File generato o curato a mano?** Come `config/theme_categories.csv`
   (curato) o rigenerato a ogni aggiornamento dati (automatico, poi rivisto)?
   I titoli cambiano raramente: probabile che generato-poi-rivisto sia giusto,
   ma va deciso, non assunto.
3. **Schema del contenuto**: un file per famiglia in `content/indicators/`
   (quale slug/id lo rappresenta?) o un nuovo `content/famiglie/<chiave>.json`
   separato dai file per id, che restano per compatibilità? Tocca anche gli
   URL canonici e i redirect dagli id vecchi.
4. **Ambito del pilota, da riconsiderare alla luce del punto 1**: BES
   (sezione 3) ha 84 famiglie pronte senza euristica, più del triplo delle
   30 del catalogo storico, ed è la fonte più economica su cui far partire
   la famiglia pilota (basta smettere di scartare le righe `Maschi`/
   `Femmine` in `scripts/update_bes_regions.py:151`). Il catalogo storico
   resta un candidato valido (es. la tripletta 345/346/347, occupazione
   20-64, che è fra le pagine con più impression), ma non è più l'unico né
   il più economico.
