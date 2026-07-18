---
name: divario-italia-design
description: Reference design tokens, components, and guidelines for Divario Italia — an editorial + cartographic data-journalism atlas of Italy's territorial divides (Istat indicators).
---

This folder is a reference copy of the Divario Italia Design System, pulled from the claude.ai/design project and maintained in sync for easy access during development.

**Use this for:**
- Looking up exact token values (colors, typography, spacing)
- Referencing component APIs and variants
- Understanding the visual language and constraints
- Building new features that should stay on-brand

**Do NOT:**
- Edit these files directly — they're read-only reference
- Import components directly from here — they're documentation only
- Treat this as a replacement for the actual source code

For the latest design specs and interactive previews, see the Design System project on claude.ai/design.

## Quick Reference

**Palette:** paper `#fbfaf7`, ink `#15233b`, accent `#e4572e`
**Type:** Archivo (display), Inter (body), Space Mono (mono)
**Shape:** square corners (border-radius: 0) everywhere except Toggle
**Borders:** 1px navy at 16% opacity; 3px accent rules on callouts
**Motion:** 120–240ms ease transitions on border-color, color, background

## Components at a Glance

| Component | Usage |
|-----------|-------|
| Button | Actions (primary, secondary, outline, ghost) |
| Tag | Theme/category chips |
| Eyebrow | Uppercase mono kickers above headlines |
| DataCard | Panel wrapper for visualizations |
| Insight | Stat blocks with label, value, caption |
| SearchBox | Full-width search input |
| SelectField | Labelled dropdown (stack or inline) |
| Toggle | On/off switch |
| MacroTab | Segmented filter tabs |
| Sparkline | Tiny trend lines |
| RankingRow | Regional ranking rows |

For detailed usage, see the component `.d.ts` files in `components/`.
