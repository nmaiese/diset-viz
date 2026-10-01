# Ricerca sulla sezione gioco

I rapporti che hanno accompagnato la costruzione di Sfida Italia, il gioco sotto `/quiz`. Sono **fotografie del 30 settembre 2026**: dicono che cosa si sapeva e che cosa si vedeva quel giorno, prima delle ondate di lavoro che hanno rifatto il gioco. Non si aggiornano. Quando un rapporto e il codice non tornano, ha ragione il codice, e il contratto vivo della sezione è [`docs/GIOCO.md`](../../GIOCO.md).

| Rapporto | Che cosa contiene | Come è verificato |
| --- | --- | --- |
| [`A-meccaniche.md`](A-meccaniche.md) | come si tiene in gioco una persona: sfida del giorno, serie, difficoltà, progressione | ricerca web, ogni fonte marcata `[V]` (aperta e letta) o `[S]` (vista solo nel risultato di ricerca), lacune dichiarate |
| [`B-identita.md`](B-identita.md) | identità visiva di un sottomarchio dentro una testata, e la proposta per il gioco | ricerca web su testate che hanno un gioco proprio |
| [`D-ux.md`](D-ux.md) | revisione del percorso di gioco e dei testi, sui giochi com'erano il 30 settembre | tutto verificato nel codice di quel giorno, con riferimenti `file:riga` |

Si leggono in quest'ordine se si vuole capire come il gioco è stato pensato: le meccaniche, l'identità, la revisione.

**Che cosa è invecchiato.** I riferimenti `file:riga` di `D-ux.md` puntano al codice di quel giorno, e molti non esistono più: il livello provinciale, la mappa, il contatore, il fatto "da portarti via" e la rinomina in inglese degli identificatori sono arrivati dopo. Il rapporto elenca difetti di quel giorno: alcuni sono stati corretti, e prima di ripartire da un suo punto si ricontrolla sul codice. `B-identita.md` propone un viola indaco con valori esadecimali che poi sono stati rifatti e verificati con `check_tokens.py`: i valori veri dei token `--game-*` stanno in `design/v1/tokens/tokens.json` e in `app/static/css/ds/system.css`, e le regole in `design/v1/SISTEMA.md`. Il nome Sfida Italia non viene da qui. `A-meccaniche.md` ha il panorama dei giochi altrui, che si legge come contesto e non come istruzione.

**Che cosa non c'è, di proposito.** Un rapporto tecnico e una revisione avversaria dello stesso periodo non sono versionati. Contenevano i passi con cui si riproducevano i difetti di allora, e il repository è pubblico: quelle ricette non ci vanno, né qui né in una PR. Se un giorno si vorranno pubblicare, prima vanno riscritti come verifica di che cosa è stato corretto, non come istruzioni.

## Che cosa non è un rapporto di ricerca

`docs/GIOCO.md` non è ricerca: è il contratto della sezione e vale per quello che il codice fa adesso. Un rapporto dice perché, `docs/GIOCO.md` dice come, e va aggiornato insieme al codice che descrive. I rapporti invecchiano e non hanno un proprietario.
