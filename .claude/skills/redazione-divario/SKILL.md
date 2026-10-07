---
name: redazione-divario
description: Scrivere, preparare o rivedere articoli del blog e schede indicatore di Divario Italia, compresi scout, brief, Gate A, Gate B, grafici e bozza HTML. Usala per la prosa del sito, non per modifiche al solo codice.
---

# Redazione Divario Italia

Leggi `content/STYLE.md` per voce, tecniche giornalistiche e tipografia; per le schede leggi anche `docs/INDICATOR_PAGES.md`. Per il contratto editoriale vigente leggi `/mnt/c/Users/Nilo/orca/specs/REDAZIONE-divario-v3.md` e `docs/design_drafts/team/PIANO.md` nelle sezioni v3 e Gate B. La v3 sostituisce brief e Gate A della v2; Gate B resta quello del PIANO. Questa skill guida le decisioni, non duplica i formati dei report.

## Due tipi di pezzo

- **Blog (`content/posts/`)**: parti da un fatto o tema reale e dalla domanda del lettore. Verifica prima le fonti, confronta almeno due angoli sostenibili e solo allora fissa la tesi. Gli indicatori del sito sono base e tassello, non la tesi; non costruire il pezzo su correlazioni fra soli indicatori interni. Il pezzo richiede almeno tre fonti esterne autorevoli di istituzioni distinte, aperte, verificate e citate, più un grafico con dati esterni. Fonte, periodo, variabile, unità e limite del dato devono risultare controllabili. Il pezzo sui medici di famiglia v2 fu fermato: molte cifre non davano un insight al lettore.
- **Scheda (`content/indicators/`)**: spiega il singolo indicatore e che cosa significa. Altri indicatori danno solo contesto; non trasformarla in un articolo su un tema. Verifica almeno una fonte esterna datata; usa i grafici dinamici esistenti quando bastano. Il grafico esterno non è obbligatorio.
- Per entrambi, privilegia dati recenti. Brief e Gate A indicano ultimo anno o periodo osservato e data della fonte. Non scambiare data della pubblicazione con anno del dato.

## Dal brief ai due gate

1. Lo scout registra fonti effettivamente aperte, URL, data, affermazione verificata e limite; ciò che non trova resta «non trovato». Il brief distingue dato, interpretazione e causa documentata. Per il blog riporta domanda, angoli verificati, tesi proposta e ruolo degli indicatori interni. Per la scheda identifica indicatore oggetto e misure di contesto.
2. **Gate A, prima della scrittura**: caporedattore di famiglia diversa dall'autore del brief valuta le prove, non una promessa di ricerca futura. Usa `lavoro/<chiave>/gate-a.md` nel formato v3: tipo di pezzo, domanda, ultimo dato, fonti, grafico esterno per il blog, cinque criteri con prove e limiti, SHA e hash del brief corrente. Solo `PASSA` v3 valido sul brief corrente avvia lo scrittore; `FERMO` blocca. Per le schede valgono i criteri propri, senza imporre tre fonti o grafico esterno.
3. Scrittore, grafico e revisore lavorano sui materiali approvati. Il revisore verifica ogni frase con cifra, confronto, graduatoria, direzione o causa contro dato, periodo, livello, unità e denominatore. La guardia numerica può essere verde mentre la frase è falsa: nel pilota ter-12 cinque frasi non significavano ciò che dicevano i dati. La guardia `bin/py -m scripts.editoriale.guardia` riguarda le schede; non sostituisce la verifica semantica.
4. **Gate B, in revisione**: controlla T (tesi provata), R (due territori reali che fanno avanzare il racconto), L (significato concreto per il lettore nei primi due paragrafi), N (risultato non ovvio e controllo contrario). `PASSA` richiede voto almeno 4/5, zero bloccanti numerici, semantici e visivi, e report sullo SHA della bozza. Sotto 4 si riscrive; dopo due giri complessivi con bloccanti resta `FERMO` alla direzione. Il Gate B medici v3 ha mostrato il rischio di confondere quote e persone: una percentuale non diventa un conteggio senza popolazione, unità e denominatore. Persone solo se documentate da fonti citate; mai inventate o composite, né scene dedotte da medie.

## Figure, prosa e anteprima

- Grafici del blog: dati esterni verificati, fonte, anno e unità visibili. Preferisci `scripts/trend_articles/figures.py`; uno script dedicato deve restare verificabile. Controlla resa mobile e desktop, etichette, note, colori e leggibilità. La bozza HTML dei medici rese visibili linee grigie, nota fuori posto ed etichetta tagliata che i controlli sul sorgente non avevano fermato.
- Per le foto di copertina del blog, verifica pertinenza, licenza commerciale e credito; non usare immagini generate con IA o persone riconoscibili in primo piano. Per la prosa e la lunghezza del blog valgono `content/STYLE.md` e il conteggio di `scripts/editoriale/guardia_articolo.py`; un limite di mille parole copiato dalla v2 non prevale sulla regola approvata di 700–1100 per l'articolo di dati.
- Prima della pubblicazione, genera la pagina con `bin/py -m scripts.editoriale.bozza_html <slug> --radice <worktree> --pr <n>`. La bozza e l'indice stanno in `C:\Users\Nilo\orca\divario\bozze\` (`/mnt/c/Users/Nilo/orca/divario/bozze/`); apri l'HTML e l'anteprima nel Cruscotto. Rileggi testo, grafici, didascalie e fonti a 375 e 1100 px. La direzione approva prima del merge, che pubblica il pezzo; per autorizzazioni e ciclo Orca segui `lancio-e-cancello-divario` e le skill comuni cui rimanda.
