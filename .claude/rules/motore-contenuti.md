---
paths:
  - "content/**/*.md"
  - "content/**/*.json"
  - "docs/intent/**"
  - "docs/reports/**"
---

# Contenuti pubblicati e intent

- La voce è in `voce-editoriale` (skill del plugin): niente trattini lunghi, niente `;`, accenti veri, un fatto detto una volta, l'anno accanto a ogni numero non dell'ultimo anno.
- I numeri nuovi seguono `grounding-fatti`: `{{fact:id}}` e `facts_used` nel frontmatter. Se il dato manca, la frase si omette.
- Le fonti stanno in `fonti` (o `sources`) con `testo` e `url`; un pezzo senza fonti non passa `motore validate`.
- Ogni file scritto sotto `content/` viene validato dall'hook `valida-pezzo`: exit 2 = difetti da correggere prima di continuare. Si corregge la frase, non si riscrive il pezzo.
- Per praticandoildiritto ogni norma citata segue `citazioni-normative` e porta lo stato di vigenza.
- Un intent in `docs/intent/` ha il frontmatter di `docs/intent/README.md`; il nome del file è l'id; solo una persona lo porta a `approvato`.
- Non si tocca `docs/roadmap.md` a mano: si rigenera.
