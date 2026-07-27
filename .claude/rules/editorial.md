---
paths:
  - "content/**"
---

# Prosa: blog e pagine indicatore

**La voce e' una sola e la possiede [`content/STYLE.md`](../../content/STYLE.md)**,
per il blog e per le pagine indicatore. Le regole assolute, care da rompere e
gratis da ripetere: niente em-dash `—`, niente en-dash `–`, niente `;`, niente
`…`; virgole o due frasi, gli intervalli scritti "dal 1981 al 2024". Solo
numeri veri e verificabili, mai una fonte inventata. I link a un indicatore
usano il percorso canonico (`/indicatore/<slug>/ter-105`), mai
`/?indicator=...` ne' `/atlante?indicator=...` (`tests/test_url_migration.py`
fallisce su quelli). Il Markdown ha `smarty` spento apposta: `--` e `...`
restano come sono, tenere pulito il sorgente.

La scala su cui si misura un articolo e'
[`docs/WRITING_RUBRIC.md`](../../docs/WRITING_RUBRIC.md): dieci criteri, sotto
14 su 20 non e' pronto.

## Pagine indicatore

La prosa vive in `content/indicators/`, **un file per articolo**
(`scripts/indicator_store.py` possiede layout e formattazione): un `lead` piu'
quattro sezioni ordinate (`definizione`, `quadro`, `dinamica`, `limiti`). Una
sezione non scritta viene composta dai dati al render. Un articolo dichiara
`"level"` e viene usato solo a quel livello. Prima di toccare la pagina o il
view model: [`docs/INDICATOR_PAGES.md`](../../docs/INDICATOR_PAGES.md).

Sempre dal brief deterministico, mai da chiamate API ad hoc:

```bash
.venv/bin/python -m scripts.indicator_brief ter-178     # tutto su un indicatore
python3 scripts/definition_check.py --show ter-178      # che cosa conta, per la fonte
.venv/bin/python -m scripts.text_queue                  # che cosa manca a un editor
.venv/bin/python -m scripts.review_queue                # che cosa manca a un lettore
python3 scripts/prose_lint.py --summary                 # la prosa, come numero
```

La seconda riga e' la meno ovvia: confronta la prosa con la **definizione**
della fonte, non con la serie. Esiste perche' rileggere undici articoli contro
i dati ha trovato zero errori aritmetici e quattro descrizioni sbagliate di
che cosa l'indicatore conta. Le classi di errore che solo una lettura trova
stanno nella skill `indicator-review` (`.claude/skills/indicator-review/`).
