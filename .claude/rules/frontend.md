---
paths:
  - "frontend/**"
  - "app/static/css/**"
---

# Frontend

`frontend/` non e' piu' una SPA. La build di Vite ha due entry
(`frontend/vite.config.js`): `game`, il quiz in React (`src/game/`, servito
dalle pagine `game*.html` sotto `/quiz`), e `site`, il controllo di accesso
della testata in JavaScript senza framework (`src/site/auth.js`, caricato da
`blog_base.html` su ogni pagina, che espone `window.diAuth`). React resta solo
per il gioco. L'atlante e il confronto React se ne sono andati il 25 settembre
2026: sono pagine della 1.0 rese dal server, con le loro isole in
`app/static/js/` (`atlante.js`, `confronto.js`), che non passano da Vite.

Dopo ogni modifica a `frontend/src/*`, **ricompila prima di provare l'app
servita**:

```bash
cd frontend && npm run build && cd ..
```

La build finisce committata in `app/static/dist/`. Audit:
`cd frontend && npm audit --audit-level=low`.

## Un solo sistema grafico

L'identita' del sito e' la **1.0, direzione "Cronaca"**, e sta tutta in
`app/static/css/ds/system.css`: pagina bianca `--bg`, inchiostro `--ink`, un
solo accento arancio bruciato `--accent`, rampa dati blu `--seq-1..6`, font
**Sofia Sans / Sofia Sans Semi Condensed** (servite da `fonts.css`). E' l'unico
posto dove si cambia un colore, e i valori nascono da
`design/v1/tokens/tokens.json`. I nomi del sistema 2026 (`--coral-*`,
`--teal-*`, `--n-*`, `--paper`...) esistono ancora e puntano ai valori nuovi:
il "corallo" di quei nomi e' l'arancio bruciato.

Le pagine della 1.0 caricano `css/ds/components.css` e il CSS della loro pagina
(`css/ds/pages/`) al posto di `site.css`, attraverso il blocco `page_css` di
`blog_base.html`. `chrome.css` (testata, piede, transizioni fra pagine,
account) lo caricano tutte, le pagine del gioco comprese.

Due errori che non fanno fallire niente:

- **un colore cotto** (un hex o un `rgba()`) non segue il tema scuro. E' il
  difetto che teneva il masthead dell'atlante chiaro con la pagina scura, e la
  mappa sulla rampa chiara. In JS un `var()` non si risolve in un attributo di
  presentazione (`fill=`): va messo in `style`.
- **l'accento e' dell'interfaccia**, non un colore dei dati. Venti barre tutte
  arancio lo svalutano dove serve: la serie di contesto e' `--cmp-*`, l'accento
  resta all'elemento in evidenza. E una serie non si dipinge col colore del
  testo.
