# Regole per le pagine indicatore

Le pagine indicatore devono aiutare una persona a capire il dato, confrontare i
territori, verificare la fonte e riusare la serie. Non sono contenitori SEO
riempiti con frasi intercambiabili.

## Risposte obbligatorie

Ogni scheda deve rendere visibili, in questo ordine logico:

1. Il nome dell'indicatore e una definizione comprensibile.
2. Il perimetro, compresi popolazione, fascia di età, genere, numeratore,
   denominatore e unità quando disponibili nella definizione della fonte.
3. Un esempio numerico che spieghi che cosa rappresenta il valore.
4. La direzione, oppure l'assenza di una direzione univoca.
5. Il limite principale e ciò che il dato non consente di concludere.
6. L'ultimo anno, la copertura territoriale, la fonte e i download disponibili.
7. Il confronto con l'anno precedente disponibile.
8. Il trend di lungo periodo, quando esistono almeno due anni confrontabili.
9. Un collegamento all'atlante, alla metodologia, al tema o a un indicatore
   strettamente collegato.

La denominazione amministrativa originale può restare nei metadati e nel blocco
della fonte. Il testo principale deve tradurla in italiano chiaro senza cambiare
il significato statistico.

## Confronto con l'ultimo anno

Il confronto usa l'ultimo anno pubblicato e l'anno precedente effettivamente
disponibile nella stessa serie. Se manca un anno intermedio, il testo deve indicare
entrambi gli anni e non deve chiamarlo confronto annuale.

Regole di calcolo e scrittura:

- Confrontare solo i territori con un valore in entrambi gli anni.
- Dichiarare quanti territori compongono la base comune.
- Chiamare il risultato `media semplice dei valori regionali`, non `media
  Italia` o `media nazionale`.
- Per tassi e quote percentuali, esprimere le variazioni in punti percentuali.
- Indicare quante regioni aumentano, diminuiscono o restano stabili.
- Mostrare la maggiore diminuzione e il maggiore aumento solo se esistono.
- Usare `migliora`, `peggiora` o `favorevole` solo quando la direzione
  dell'indicatore è revisionata.
- Per indicatori contestuali descrivere soltanto aumento, diminuzione o
  stabilità.
- Non attribuire cause a una variazione osservata.

Se la serie ha un solo anno, la pagina deve dichiarare che il confronto temporale
non è disponibile. Non va costruita una frase sostitutiva.

## Trend di lungo periodo

Il confronto tra primo e ultimo anno resta separato dalla variazione più recente.
Deve indicare gli anni, l'unità e la base territoriale. Una variazione percentuale
può accompagnare la variazione assoluta, ma non deve sostituirla quando l'unità è
necessaria per capire la scala.

## Accuratezza

- La definizione della fonte è il riferimento principale.
- Numeratore e denominatore non vanno dedotti quando la fonte non li esplicita.
- Una media regionale non sostituisce un indicatore nazionale ponderato.
- Una correlazione territoriale non dimostra una causa.
- Una graduatoria non dimostra l'efficacia di una politica.
- Totale, uomini e donne sono perimetri distinti e non vanno confusi.
- Un divario tra due tassi va espresso in punti percentuali e non descrive da
  solo il livello complessivo dei due tassi.

## SEO e struttura

La pagina serve prima di tutto gli intenti di definizione, confronto, fonte e
riuso del dato. Titolo, descrizione, H1 e testo visibile devono essere coerenti.
Ogni pagina indicizzabile deve avere:

- titolo e descrizione unici
- una sola H1 descrittiva
- fonte, periodo, territorio e unità visibili
- HTML server-rendered con testo utile anche senza JavaScript
- canonical autoreferenziale
- Dataset JSON-LD coerente con il contenuto e i download visibili
- link alla metodologia e al contesto tematico

Non aggiungere FAQ generiche o paragrafi di riempimento. Le varianti quasi
duplicate, incomplete o obsolete seguono le regole di indicizzazione definite in
`app/profiles.py`.

## Verifica

Prima della pubblicazione:

```bash
.venv/bin/python -m unittest discover -s tests -v
python3 /home/nilo/dev/ai-agents/skills/italian-product-copywriter/references/audit_editorial_quality.py .
rg -n "[—–;]" app/templates app/indicator_notes.py docs/INDICATOR_PAGES.md
git diff --check
```

Controllare almeno una pagina per ciascuna famiglia: percentuale, rapporto,
valore assoluto, unità per abitante, punteggio, differenza tra tassi, serie con un
solo anno e indicatore contestuale.
