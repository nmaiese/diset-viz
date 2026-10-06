# RAPPORTO — UX immagini prima/dopo (Divario Italia)

**Cosa fatto:** 28 screenshot (7 pagine × desktop 1440px / mobile 375px × prima/dopo) su https://divarioitalia.it, tema chiaro, banner consenso chiuso. Iniettato `layout.css` (contenitore 1200px centrato, padding clamp, ritmo verticale 48–64px desktop / 32–40px mobile) + `proposta.css` (contrasto, tipografia) + `trasforma.js` (DOM). Singola istanza Chromium, pausa 1s.

**Numeri chiave (desktop 1440px):**

| pagina | main prima | main dopo | cpl prima | cpl dopo | scroll X |
|--------|-----------|----------|----------|---------|----------|
| home | 1440 | 1200 | n/d | n/d | no → no |
| regioni | 1440 | 1200 | n/d | n/d | no → no |
| blog | 1440 | 1200 | n/d | n/d | no → no |
| atlante | 1440 | 1200 | 65 | 113 | no → no |
| articolo | 1440 | 1200 | 96 | 96 | no → no |
| regione | 1440 | 1200 | 100 | 98 | no → no |
| scheda | 1440 | 1200 | 80 | 67 | no → no |

**Mobile 375px:** main resta 375px, niente scroll orizzontale (fix `max-width:100%` + `overflow-x:hidden`). cpl 39–48, tutti in range leggibile.

**Dove l'impianto "dopo" ROMPE / peggiora:**
- **Atlante desktop**: cpl sale 65→113 (troppo largo, >80 ch). Il contenitore 1200px + prose 65ch non basta: il font di base è piccolo e la colonna si allarga.
- **Articolo desktop**: cpl fermo 96 (già >80 prima). Stesso problema.
- **Regione desktop**: cpl 100→98 (marginale miglioramento, ma ancora >80).
- **Scheda desktop**: cpl 80→67 (migliora, ora in range 45–80).

**Causa:** `max-width: 1200px` sul main + `max-width: 65ch` su `.prose`/`.indicator-article` ecc. non garantisce ≤80 ch se il font-size computato è <16px o se i selettori non coprono tutto il testo. La proposta.css alza il font a `max(16px, ...)` ma non su tutti i contesti.

**Cosa NON provato:**
- Tema scuro (solo chiaro).
- Viewport 1920px e 1024px (solo 1440 e 375).
- Pagine che rispondono non-200 (tutte 7 OK).
- Stati interazione (hover, focus, dettagli aperti/chiusi).
- Accessibilità screen reader, stampa, reduced-motion.

**File prodotti in `/mnt/c/Users/Nilo/orca/direzione/review/ux-immagini/`:**
- 28 PNG: `<pagina>_<desktop|mobile>_<prima|dopo>.png`
- `layout.css` (impianto), `proposta.css`, `trasforma.js` (copie)
- `misure_immagini.json` (dati grezzi)
- `confronto.html` (griglia immagini + tabelle misure)
- `RAPPORTO.md` (questo file)