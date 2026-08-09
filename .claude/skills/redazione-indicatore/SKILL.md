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

## Memoria editoriale

Usano memoria soltanto `source-researcher` e `skeptical-editor`, entrambi con
scope `project`. All'avvio devono consultare il proprio `MEMORY.md`:

- `.claude/agent-memory/source-researcher/MEMORY.md`
- `.claude/agent-memory/skeptical-editor/MEMORY.md`

La memoria orienta domande e controlli, non prova fatti. Ogni claim, URL, metodo
o limite usato nel pezzo va verificato nella run corrente. I teammate restano
in sola lettura e restituiscono `memory_candidates`; solo il lead promuove una
voce, modificando esclusivamente i due file sopra. Rifiutare valori correnti,
classifiche, deduzioni sul singolo articolo, preferenze stilistiche e URL senza
contesto.

Un candidato deve contenere almeno `categoria`, `apprendimento`,
`verified_on`, `recheck_after`, `ambito`, `limiti` e una prova
(`evidence_url` per le fonti, `evidenza` per la revisione). Promuovere solo
con prova riaperta nella run e utilità oltre l'indicatore corrente. Accorpare i
duplicati, rimuovere le voci scadute non riconfermate e mantenere `MEMORY.md`
breve.

Nelle Routine ogni run parte da un nuovo clone della branch predefinita:
l'aggiornamento diventa memoria delle run future soltanto dopo il merge della
PR che lo contiene. Non scrivere direttamente sulla branch predefinita (`master` in questa
repository) per accelerare questa persistenza.

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

- pubblicato: `{"articoli":[<uscita di lab.pubblica>],"fermati":[],"memoria":<consuntivo>}`
- fermato: `{"articoli":[],"fermati":[{"codice":"<codice>","motivo":"<motivo>"}],"memoria":<consuntivo>}`

Il `consuntivo` ha `consultata` e `aggiornata` come liste di ruoli, più i
conteggi `candidati`, `promossi` e `scartati`. Gli hook lo conservano
nell'esito della run, visibile nel dettaglio della dashboard.

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
7. Valutare i `memory_candidates` di ricercatore e revisore. Il lead promuove
   solo apprendimenti durevoli e registra candidati, promossi e scartati.
8. Il lead salva la bozza, esegue
   `bin/py -m lab.controlla <codice> --bozza <percorso> --salva`, poi
   `bin/py -m lab.pubblica <codice> --bozza <percorso>` e i test pertinenti.
9. Copiare uscita e consuntivo memoria nella descrizione JSON della sentinella,
   completarla e chiedere ai teammate di chiudersi.

Persistenza consigliata, senza aggiungere script:

`data/lab/team/<run-id>/dossier.json`, `evidence/data.json`,
`evidence/sources.json`, `evidence/search.json`, `angle/decision.json`,
`draft.json`, `reviews/*.json`, `final.json`.

Ogni file lo scrive il lead copiando un risultato strutturato, non il teammate.
