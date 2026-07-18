# Divario Italia — Design System

**Divario Italia** ([divarioitalia.it](https://divarioitalia.it)) is a Flask +
React **atlas of Italy's territorial divides**, built on Istat regional
development indicators. It pairs an interactive atlas (choropleth maps,
rankings, time series across 377 indicators, 20 regions, 1981–2025) with a
data-driven SEO blog and a quality-of-life ranking for regions and provinces.

The identity is **editorial and cartographic**: warm paper, dark navy ink, a
single hot terracotta accent, heavy Archivo headlines over a faint ruled grid,
and Space Mono for every label and number. It reads like a serious data-journalism
publication, in Italian.

This design system packages that identity — tokens, fonts, reusable React
components, and full interactive UI-kit recreations of the product's surfaces —
so agents can build on-brand Divario Italia interfaces and assets.

---

## Visual Foundations

**Color** — A tight, unbranded-feeling palette. Warm off-white paper
(`#fbfaf7`), white panels, dark-navy ink (`#15233b`) with softer navy
(`#2b3a55`) and muted grey-blue (`#6b7785`) for secondary text. Exactly **one**
accent: a terracotta vermilion (`#e4572e`), used sparingly for links, active
states, the primary button, and the accent-soft wash (`rgba(228,87,46,0.12)`).\
Borders and gridlines are **navy at low alpha** (`--line` .16, `--grid` .09), never
grey. Status: gains use a restrained green (`#2f8f5b`); losses reuse the accent.
No gradients anywhere except the sequential **choropleth ramp** (`#e7ecf3 →
#15233b`) and the `linear-gradient` used to draw the faint ruled grid.

**Type** — Three families, three jobs. **Archivo** (400–800) for display: heavy
(800), tight headlines with negative tracking (`-0.015em`) and `line-height: .98`.
**Inter** (400–700) for body and reading (prose 17px / line-height 1.6).
**Space Mono** (400/700) for everything metadata: eyebrows, labels, coverage
pills, table headers, and all numbers (tabular). Mono labels are UPPERCASE with
generous letter-spacing (`.06–.08em`). Loaded from Google Fonts (`Archivo`,
`Inter`, `Space Mono`) — the product loads the same three via `<link>`.

**Shape & borders** — The brand is **emphatically square**: `border-radius: 0`
everywhere. The single exception is the on/off `Toggle` knob (a 999px pill).
Surfaces are separated by 1px hairline borders and, when raised, a soft navy
shadow (`0 16px 44px rgba(21,35,59,.10)`); the dark tooltip uses a tighter
shadow. Callouts and insights carry a **3px accent left-rule** instead of a fill.

---

## Components

**Core**
- `Button` — primary (accent fill), secondary (ink-outlined), outline, ghost
- `Tag` — solid (accent-soft filled), pill (hairline mono)
- `CoveragePill` — metadata pill with optional states
- `Eyebrow` — uppercase Space Mono kicker (accent or muted)
- `BrandMark` — Italy+bars mark + Archivo wordmark lockup

**Data**
- `DataCard` — panel wrapper with mono kicker + Archivo title
- `Insight` — stat block with label, value, caption; region variant
- `Sparkline` — tiny SVG trend line with end dot
- `RankingRow` — ranking row with track bar, region-first layout

**Forms**
- `SearchBox` — full-width input with leading glyph
- `SelectField` — labelled native select with chevron; stack or inline layout
- `Toggle` — on/off switch, the one rounded element

**Navigation**
- `MacroTab` — segmented filter tab with optional count

---

## Tokens

All design tokens are CSS custom properties, prefixed with `--`:

**Colors**
- `--paper`, `--panel`, `--ink`, `--ink-soft`, `--muted`, `--accent`, `--accent-soft`
- `--line`, `--grid` (navy at low alpha for borders)
- `--positive`, `--negative` (semantic status)
- `--map-ramp-from`, `--map-ramp-to` (choropleth scale)
- `--shadow`, `--shadow-tooltip`

**Typography**
- Display: `--text-hero`, `--text-title`, `--text-h2`, `--text-h3`
- Body: `--text-prose`, `--text-body`, `--text-body-lg`
- Meta: `--text-sm`, `--text-xs`, `--text-xxs`
- Weights: `--weight-regular` through `--weight-black`
- Leading: `--leading-tight`, `--leading-snug`, `--leading-normal`, `--leading-body`
- Tracking: `--tracking-display`, `--tracking-eyebrow`, `--tracking-label`

**Spacing**
- Scale: `--space-1` through `--space-24` (4px to 64px)
- Layout: `--gutter`, `--measure-prose`, `--measure-wide`
- Radii: `--radius-0` (0), `--radius-pill` (999px)
- Borders: `--border-hairline`, `--rule-accent`
- Motion: `--dur-fast`, `--dur`, `--dur-slow`

---

## Reference

Source repository: [nmaiese/diset-viz](https://github.com/nmaiese/diset-viz)
- `frontend/src/styles.css` — atlas stylesheet (token source)
- `app/static/css/site.css` — blog + SEO page styles
- `content/STYLE.md` — editorial voice guide (binding for copy)
