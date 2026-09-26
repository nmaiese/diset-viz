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
4 settembre insieme al lint della prosa. La vecchia verifica automatica esterna
è dismessa. Prima di pubblicare si controllano struttura, cifre, link interni,
fonti e marcatori di figura con i test locali e con una rilettura umana. Una
media semplice delle regioni non è una media nazionale.

## Pagine indicatore

La prosa vive in `content/indicators/`, **un file per articolo**
(`scripts/indicator_store.py` possiede layout e formattazione): un `lead` più
quattro sezioni ordinate (`definizione`, `quadro`, `dinamica`, `limiti`). Una
sezione non scritta viene composta dai dati al render. Un articolo dichiara
`"level"` e viene usato solo a quel livello. Prima di toccare la pagina o il
view model: [`docs/INDICATOR_PAGES.md`](../../docs/INDICATOR_PAGES.md).

Un file di `content/indicators/` e' Markdown con frontmatter, come un post del
blog: i campi in testa (`fonti` con `testo` e `url`, `vintage`, `level`, `h1`,
`seo_title`), poi il lead, poi le sezioni, ognuna aperta da
`<!-- sezione: ruolo -->` e col suo `## titolo`. Il contratto e' quello di
`scripts/indicator_store.py`. Le cifre devono essere ricavate dai dati del
progetto e verificate. `fonti` puo' restare vuota quando non c'e' contesto
esterno verificabile (non e' un difetto, si segnala nella PR).

Il formato e' Markdown perche' la PR e' il momento in cui il pezzo si legge: in
JSON una sezione stava su una riga sola con gli a capo scritti `\n`, e il diff
di una correzione non si poteva giudicare.

La definizione si controlla con lo strumento deterministico, mai con chiamate
API ad hoc:

```bash
bin/py scripts/definition_check.py --show ter-178      # che cosa conta, per la fonte
```

Non esistono oggi un dossier o una coda editoriali operativi. Un futuro
workflow verrà progettato da zero dentro questo progetto.

Il controllo confronta la prosa con la **definizione**
della fonte, non con la serie. Esiste perché rileggere undici articoli contro
i dati ha trovato zero errori aritmetici e quattro descrizioni sbagliate di
che cosa l'indicatore conta. Le classi di errore che solo una lettura
trova le trova chi rilegge, non uno strumento.
