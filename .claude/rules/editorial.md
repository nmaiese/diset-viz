---
paths:
  - "content/**"
---

# Prosa: blog e pagine indicatore

**La voce è una sola e la possiede [`content/STYLE.md`](../../content/STYLE.md)**,
per il blog e per le pagine indicatore. Le regole assolute, care da rompere e
gratis da ripetere: niente em-dash `—`, niente en-dash `–`, niente `;`, niente
`…`; virgole o due frasi, gli intervalli scritti "dal 1981 al 2024". Solo
numeri veri e verificabili, mai una fonte inventata. I link a un indicatore
usano il percorso canonico (`/indicatore/<slug>/ter-105`), mai
`/?indicator=...` né `/atlante?indicator=...` (`tests/integration/test_url_migration.py`
fallisce su quelli). Il Markdown ha `smarty` spento apposta: `--` e `...`
restano come sono, tenere pulito il sorgente.

Un articolo non si misura con una rubrica a punti: quella è stata ritirata il
4 settembre insieme al lint della prosa. Quello che ferma un pezzo sono le tre
guardie di `motore verifica`, nel repo della redazione: una cifra che non sta
nel dossier, un link interno che non esiste, una fonte che non risponde. Il
resto è una lettura, e i rilievi hanno una gravità.

## Pagine indicatore

La prosa vive in `content/indicators/`, **un file per articolo**
(`scripts/indicator_store.py` possiede layout e formattazione): un `lead` più
quattro sezioni ordinate (`definizione`, `quadro`, `dinamica`, `limiti`). Una
sezione non scritta viene composta dai dati al render. Un articolo dichiara
`"level"` e viene usato solo a quel livello. Prima di toccare la pagina o il
view model: [`docs/INDICATOR_PAGES.md`](../../docs/INDICATOR_PAGES.md).

Sempre dal brief deterministico, mai da chiamate API ad hoc:

```bash
python3 scripts/definition_check.py --show ter-178      # che cosa conta, per la fonte
```

Il dossier e la coda stanno nella redazione:
`motore brief divarioitalia ter-178` e `motore coda divarioitalia`.

La seconda riga è la meno ovvia: confronta la prosa con la **definizione**
della fonte, non con la serie. Esiste perché rileggere undici articoli contro
i dati ha trovato zero errori aritmetici e quattro descrizioni sbagliate di
che cosa l'indicatore conta. Le classi di errore che solo una lettura
trova le trova chi rilegge, non uno strumento.
