# RAPPORTO — UX immagini prima/dopo (Divario Italia) — secondo giro

**Cosa fatto:** 42 screenshot (7 pagine × desktop 1920px, desktop 1440px, mobile 375px × prima/dopo) su https://divarioitalia.it, tema chiaro, banner consenso chiuso. Iniettato `layout.css` (contenitore 1200px centrato, padding clamp, ritmo verticale 48–64px desktop / 32–40px mobile) + `proposta.css` (contrasto, tipografia, ora limitato a `main`) + `trasforma.js` (DOM). Singola istanza Chromium, pausa 1s.

**Numeri chiave (desktop 1440px):**

| pagina | main prima | main dopo | cpl prima | cpl dopo | scroll X |
|--------|-----------|----------|----------|---------|----------|
| home | 1440 | 1200 | n/d | n/d | no → no |
| regioni | 1440 | 1200 | n/d | n/d | no → no |
| blog | 1440 | 1200 | n/d | n/d | no → no |
| atlante | 1440 | 1200 | 65 | 113 | no → no |
| articolo | 1440 | 1200 | 96 | 96 | no → no |
| regione | 1440 | 1200 | 100 | 98 | no → no |
| scheda | 1440 | 1200 | 80 | 41 | no → no |

**Numeri chiave (desktop 1920px):**

| pagina | main prima | main dopo | cpl prima | cpl dopo | scroll X |
|--------|-----------|----------|----------|---------|----------|
| home | 1920 | 1200 | n/d | n/d | no → no |
| regioni | 1920 | 1200 | n/d | n/d | no → no |
| blog | 1920 | 1200 | n/d | n/d | no → no |
| atlante | 1920 | 1200 | 65 | 113 | no → no |
| articolo | 1920 | 1200 | 96 | 96 | no → no |
| regione | 1920 | 1200 | 100 | 98 | no → no |
| scheda | 1920 | 1200 | 80 | 41 | no → no |

**Mobile 375px:** main resta 375px, niente scroll orizzontale. cpl 39–48, tutti in range leggibile.

**Dove l'impianto "dopo" ROMPE / peggiora:**
- **Atlante desktop**: cpl sale 65→113 (troppo largo, >80 ch). Il selettore `.intro` riceve `max-width: 65ch` ma `proposta.css` non alza il font-size su `.intro` (solo su `.prose`, `.indicator-article`, ecc.), quindi `ch` resta piccolo e la colonna non si stringe. **Atlante è un'interfaccia tabellare**, non prosa lunga: la colonna 65ch non va applicata qui.
- **Articolo desktop**: cpl fermo 96 (già >80 prima). Il contenitore 1200px + `max-width: 65ch` su `.prose.art-body` non basta perché il font-size computato è >16px (proposta.css lo porta a 16px minimo ma il container è largo).
- **Regione desktop**: cpl 100→98 (marginale miglioramento, ancora >80). Stesso problema: `.prose` su `.ritratto` e `.regione-intro` ma font-size >16px allarga la colonna.
- **Scheda desktop**: cpl 80→41 (migliora, ora in range 45–80). `.indicator-article.prose` funziona perché il font-size è controllato.

**Causa:** `max-width: 65ch` sul blocco di prosa + `font-size: max(16px, ...)` in `proposta.css` non garantisce ≤80 ch se il font-size computato è ≥16px (65ch × 16px ≈ 1040px, entra in 1200px ma la misura conta caratteri reali su riga). Serve `max-width` in `ch` più basso (es. 55ch) o `max-width` in pixel sul contenitore di prosa.

**Footer / Header:** font-size invariati (footer h2 14px, footer link 16px, header nav 16px). Fix: `proposta.css` ora limita tutte le regole tipografiche a `main` (es. `main h1`, `main .prose p`, ecc.).

**Densità (desktop 1440px):**

| pagina | stato | schermi | blocchi main | parole 1° schermo | link 1° schermo | link/schermo (medio) |
|--------|-------|---------|--------------|-------------------|-----------------|---------------------|
| home | prima | 8.04 | 9 | 220 | 0 | 3.3 |
| home | dopo | 8.64 | 9 | 220 | 0 | 1.7 |
| regioni | prima | 4.49 | 2 | 227 | 6 | 4.5 |
| regioni | dopo | 4.57 | 2 | 223 | 6 | 3.0 |
| blog | prima | 6.27 | 1 | 201 | 3 | 1.7 |
| blog | dopo | 6.20 | 1 | 201 | 3 | 1.7 |
| atlante | prima | 44.44 | 1 | 223 | 1 | 1.2 |
| atlante | dopo | 44.64 | 1 | 223 | 1 | 1.1 |

**Densità (desktop 1920px):**

| pagina | stato | schermi | blocchi main | parole 1° schermo | link 1° schermo | link/schermo (medio) |
|--------|-------|---------|--------------|-------------------|-----------------|---------------------|
| home | prima | 6.68 | 9 | 275 | 0 | 2.7 |
| home | dopo | 7.21 | 9 | 235 | 0 | 3.7 |
| regioni | prima | 3.74 | 2 | 320 | 6 | 5.5 |
| regioni | dopo | 3.81 | 2 | 277 | 6 | 5.5 |
| blog | prima | 5.26 | 1 | 201 | 3 | 1.5 |
| blog | dopo | 5.16 | 1 | 270 | 8 | 4.0 |
| atlante | prima | 37.80 | 1 | 258 | 1 | 1.5 |
| atlante | dopo | 39.19 | 1 | 258 | 1 | 1.4 |

**Cosa dice la tabella densità:** Dopo l'impianto, la densità è **lievemente più bassa** su home/regioni/blog (più schermi, meno link/schermo), **stabile** su atlante. L'aumento di schermi su home (+0.6) è dovuto al ritmo verticale `clamp(48px, 4vw, 64px)` che a 1440px dà ~58px vs originale più compatto.

**Larghezze contenitore e blocchi a 1920px:**
- main: prima 1920px → dopo 1200px (centrato)
- max child width: prima ~1440-1920px → dopo ≤1200px (eccezioni full-width: mappe, hero, pagehead)
- Padding laterale: `clamp(1rem, 4vw, 3rem)` = 77px a 1920px

**Cosa NON provato:**
- Tema scuro (solo chiaro).
- Viewport 1024px e 768px (solo 1920, 1440, 375).
- Pagine che rispondono non-200 (tutte 7 OK).
- Stati interazione (hover, focus, dettagli aperti/chiusi).
- Accessibilità screen reader, stampa, reduced-motion.
- Atlante: non applicata colonna 65ch (è interfaccia, non prosa).

**File prodotti in `scripts/misure/` e `lavoro/`:**
- 42 PNG: `<pagina>_<desktop1920|desktop1440|mobile>_<prima|dopo>.png` (14 nuovi desktop1920 + 28 esistenti)
- `layout.css` (aggiornato: selettori prosa estesi), `proposta.css` (aggiornato: scope `main`), `trasforma.js`
- `misure_immagini.json`, `densita.json` (dati grezzi)
- `confronto.html` (griglia 42 immagini + tabelle misure)
- `RAPPORTO.md` (questo file)