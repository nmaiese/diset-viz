---
name: redazione-indicatore
description: >-
  Avviare e guidare un vero Agent Team editoriale per creare o riscrivere un
  articolo indicatore di Divario Italia, dalla generazione del dossier alla
  ricerca parallela, conferenza d'angolo, bozza, revisione e pubblicazione.
  Usare quando l'utente chiede una run agentica, un team di redazione o la
  scrittura completa di un indicatore.
---

# Guidare il team editoriale

La sessione principale è `editor-in-chief` e resta lead per tutta la run. Usare
un solo indicatore per sessione. Creare un Agent Team reale, non un workflow e
non subagenti. I teammate non possono creare team o subagenti.

## Perimetro

Il lead è l'unico che esegue comandi, scrive file, salva la bozza e pubblica.
Tutti i teammate lavorano in sola lettura e consegnano tramite task e messaggi.
Aspettare i teammate prima di sintetizzare.

Usare esattamente questi teammate e nomi:

- `data-editor`, tipo `data-editor`
- `source-researcher`, tipo `source-researcher`
- `search-strategist`, tipo `search-strategist`
- `data-journalist`, tipo `data-journalist`
- `skeptical-editor`, tipo `skeptical-editor`

Nel prompt di spawn ordinare a ciascuno di invocare le skill nominate nel corpo
della sua definizione. Il frontmatter `skills` non viene applicato ai teammate.

## Protocollo dei task e dashboard

Creare i task appena diventano eseguibili, non tutti in anticipo. Il subject
deve avere esattamente questa forma:

`[redazione:<ruolo>:<fase>] <codice> - <titolo>`

Ruoli ammessi: `lead`, `data-editor`, `source-researcher`,
`search-strategist`, `data-journalist`, `skeptical-editor`. Fasi ammesse:
`dossier`, `ricerca`, `angolo`, `scrittura`, `verifica`, `pubblicazione`,
`chiusura`.

Creare subito una sentinella e lasciarla aperta:

`[redazione:lead:chiusura] <codice> - chiusura del run`

Completarla soltanto dopo controlli e pubblicazione, oppure dopo avere deciso
esplicitamente di fermare il pezzo. Prima di completarla, aggiornare la sua
descrizione con l'esito JSON usato dal cruscotto:

- pubblicato: `{"articoli":[<uscita di lab.pubblica>],"fermati":[]}`
- fermato: `{"articoli":[],"fermati":[{"codice":"<codice>","motivo":"<motivo>"}]}`

Gli hook traducono task ed esito nella stessa dashboard del workflow attuale.

## Sequenza

1. Eseguire `bin/py -m lab.dossier <codice>` e salvare il percorso del dossier.
2. Avviare in parallelo i task di `data-editor`, `source-researcher` e
   `search-strategist`.
3. Fare la conferenza d'angolo. `data-journalist` propone due tesi,
   `skeptical-editor` le attacca, i tre ricercatori rispondono direttamente. Il
   lead sceglie e registra motivazione e prove scartate.
4. Assegnare una sola bozza a `data-journalist`.
5. Revisionare in parallelo con `data-editor`, `source-researcher`,
   `search-strategist` e `skeptical-editor`.
6. Fare al massimo una correzione mirata con `data-journalist`. Se resta un
   rilievo `alta`, fermare senza pubblicare.
7. Il lead salva la bozza, esegue
   `bin/py -m lab.controlla <codice> --bozza <percorso> --salva`, poi
   `bin/py -m lab.pubblica <codice> --bozza <percorso>` e i test pertinenti.
8. Copiare l'uscita di pubblicazione o arresto nella descrizione JSON della
   sentinella, completarla e chiedere ai teammate di chiudersi.

Persistenza consigliata, senza aggiungere script:

`data/lab/team/<run-id>/dossier.json`, `evidence/data.json`,
`evidence/sources.json`, `evidence/search.json`, `angle/decision.json`,
`draft.json`, `reviews/*.json`, `final.json`.

Ogni file lo scrive il lead copiando un risultato strutturato, non il teammate.
