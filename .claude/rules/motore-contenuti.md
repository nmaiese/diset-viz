---
paths:
  - "content/**/*.md"
  - "content/posts/**"
  - "docs/intent/**"
  - "docs/reports/**"
---

# Contenuti pubblicati e intent

- Ogni pezzo pubblicato risponde alla prova dell'insight (skill `voce-editoriale`): notizia nel lead, il perché documentato, che cosa cambia per le persone, un confronto con un parente, la domanda con cui il lettore è arrivato. Il pubblico è nel campo `pubblico` di `sites/<sito>.yaml`.
- La voce è in `voce-editoriale` (skill del plugin): niente trattini lunghi, niente `;`, accenti veri, un fatto detto una volta, l'anno accanto a ogni numero non dell'ultimo anno.
- I numeri nuovi seguono `grounding-fatti`: `{{fact:id}}` e `facts_used` nel frontmatter. Se il dato manca, la frase si omette.
- Le fonti stanno in `fonti` (o `sources`) con `testo` e `url`; un post senza fonti non passa `motore validate`.
- **Articoli-indicatore di diset-viz** (`content/indicators/*.json`): il contratto è quello di `scripts/indicator_store.py` (niente frontmatter, cifre dal dossier, `fonti` può essere vuota quando gli scout non trovano contesto verificabile). Questa rule non li copre; `motore validate` li tratta come JSON e non boccia una lista `fonti` vuota, ma la segnala nella PR.
- Ogni file scritto sotto `content/` viene validato dall'hook `valida-pezzo`: exit 2 = difetti da correggere prima di continuare. Si corregge la frase, non si riscrive il pezzo.
- Per praticandoildiritto ogni norma citata segue `citazioni-normative` e porta lo stato di vigenza. Finché `sites/praticandoildiritto.yaml` ha `pubblicazione_bloccata: true`, su quel sito non si pubblica e non si scrive su Blogger: solo mirror in lettura e audit.
- Un intent in `docs/intent/` ha il frontmatter di `docs/intent/README.md`; il nome del file è l'id; solo una persona lo porta a `approvato`.
- Non si tocca `docs/roadmap.md` a mano: si rigenera.
