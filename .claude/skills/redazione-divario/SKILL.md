---
name: redazione-divario
description: Scrivere, preparare o rivedere articoli del blog e schede indicatore di Divario Italia, compresi scout, brief, Gate A, Gate B, grafici e bozza HTML. Usala per la prosa del sito, non per modifiche al solo codice.
---

# Redazione Divario Italia

Il contratto editoriale vigente è `/mnt/c/Users/Nilo/orca/specs/REDAZIONE-divario-v4.md`: brief, Gate A, Gate B, figure, cadenza e lunghezza stanno lì, con i formati dei report. Sopra la norma c'è la revisione del titolare `/mnt/c/Users/Nilo/orca/direzione/review/revisione-editoriale-2026-10-08/REVISIONE_EDITORIALE.md` (REV), che prevale su questa skill, sui gate e sulle abitudini precedenti dove li contraddice. Per voce, tecniche giornalistiche e tipografia leggi `content/STYLE.md`; per le schede anche `docs/INDICATOR_PAGES.md`. La v3 e la v2 sono storiche. Questa skill guida le decisioni, non duplica i formati.

## Che cosa è sospeso

La norma v4 non autorizza nuove pubblicazioni. La cadenza di due pezzi a settimana è sospesa finché Gate v4 è attivo e la Fase 1 di REV è chiusa; i 30 articoli AdSense contano solo se conformi ai criteri di REV §11, senza data fissa. Ogni brief con un PASSA v3 rifà Gate A v4; ogni bozza con un Gate B precedente rifà Gate B v4.

## Due tipi di pezzo

- **Blog (`content/posts/`)**: parti da un fatto o tema reale e dalla domanda del lettore. Verifica prima le fonti, confronta almeno due angoli sostenibili e solo allora fissa la risposta. Gli indicatori del sito sono base e tassello, non la tesi; non costruire il pezzo su correlazioni fra soli indicatori interni. Servono almeno tre fonti esterne autorevoli di istituzioni distinte e un grafico con dati esterni.
- **Scheda (`content/indicators/`)**: spiega il singolo indicatore e che cosa significa. Altri indicatori danno solo contesto. Titoli di sezione stabili e neutri. Una fonte esterna datata basta; il grafico esterno non è obbligatorio.
- Per entrambi, privilegia dati recenti e non scambiare data della pubblicazione con anno del dato.

## La storia prima della prosa

1. Lo scout consegna la scheda della misura, la disponibilità delle dimensioni e risultati candidati con la loro robustezza; ciò che non trova resta «non trovato». Un angolo fatto solo di primi e ultimi non è un risultato.
2. Il brief v4 fissa domanda e risposta in una frase, schema del racconto (la variante di REV §7 o §8), definizione specifica della misura, registro delle affermazioni, limiti, figure previste e fonti. La definizione dice che cosa si conta, con unità, denominatore, popolazione, territorio, periodo e release: «esprime come percentuale il fenomeno nel gruppo definito dalla fonte» non è una definizione.
3. **Gate A v4, prima della scrittura**: caporedattore di famiglia diversa dal leader. Senza definizione specifica o senza registro il gate vale FERMO anche se dice PASSA, e il parser di `scripts/editoriale/redazione.py` lo tratta così. Solo un PASSA v4 sull'hash del brief corrente avvia lo scrittore.
4. Scrittore, grafico e revisore lavorano sui materiali approvati. Il revisore verifica ogni frase con cifra, confronto, graduatoria, direzione o causa contro registro, periodo, livello, unità e denominatore. La guardia numerica può essere verde mentre la frase è falsa: nel pilota ter-12 cinque frasi non significavano ciò che dicevano i dati. `bin/py -m scripts.editoriale.guardia` riguarda le schede e non sostituisce la verifica semantica.
   Errori già visti: un tasso non è un assoluto (fecondità); figli per donna, nati e natalità non sono sinonimi; la media semplice dei territori non è il valore nazionale (pilota pensioni, 8,9% «in Italia»); le graduatorie seguono gli ordinali del sito anche a parità di valore; il Trentino-Alto Adige Istat aggrega Trento e Bolzano; le differenze si calcolano sui valori non arrotondati; una percentuale non diventa un conteggio senza popolazione e denominatore (Gate B medici).
5. **Gate B v4, in revisione**: T, R, L, N hanno i significati della norma (affermazioni sostenute da registro e fonte, confronti onesti, misura e limite prima del grafico, nessun falso primato). Voto almeno 4, zero bloccanti, massimo due giri, poi FERMO alla direzione. Persone solo da fonti citate, mai inventate o composite. Il nome del titolare compare soltanto in `/privacy`.

## Figure, prosa e anteprima

- Ogni figura porta le specifiche obbligatorie della norma (§5, da REV §6) e risponde a una domanda del brief. Preferisci `scripts/trend_articles/figures.py`; uno script dedicato deve restare verificabile. La bozza HTML dei medici rese visibili linee grigie, nota fuori posto ed etichetta tagliata che i controlli sul sorgente non avevano fermato.
- La copertina è facoltativa. Se c'è, usa `scripts/trend_articles/photo.py`, verifica pertinenza e licenza commerciale, registra `cover_credit`; niente immagini generate con IA né persone riconoscibili in primo piano. Mantieni `draft: true` fino all'ok e ometti `author` dal frontmatter (la firma viene da `config/identita.yaml`; `cover_credit.author` è il credito della foto).
- Lunghezza: le fasce della norma sono indicazioni non vincolanti. Non allungare un testo per arrivarci; il tetto di `scripts/editoriale/guardia_articolo.py` resta un avviso.
- Prima della pubblicazione, genera la pagina con `bin/py -m scripts.editoriale.bozza_html <slug> --radice <worktree> --pr <n>`. La bozza e l'indice stanno in `/mnt/c/Users/Nilo/orca/divario/bozze/`; apri l'HTML e l'anteprima nel Cruscotto. Rileggi testo, grafici, didascalie e fonti a 375 e 1100 px. La direzione approva prima del merge, che pubblica il pezzo; per autorizzazioni e ciclo Orca segui `lancio-e-cancello-divario`.
