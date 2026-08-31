---
paths:
  - "frontend/**"
  - "app/static/css/**"
---

# Frontend

Dopo ogni modifica a `frontend/src/*`, **ricompila prima di provare l'app
servita**:

```bash
cd frontend && npm run build && cd ..
```

La build finisce committata in `app/static/dist/`. Audit:
`cd frontend && npm audit --audit-level=low`.

## Due sistemi grafici, e quale vale dove

L'atlante e' migrato al **design system 2026**. `app/templates/app.html` e
`app/templates/confronto.html` caricano `css/ds/system.css` e mettono
`class="ds"` sul body: da li' in poi e' `body.ds` (specificita' 0,1,1) a
ripuntare i token che `frontend/src/styles.css` dichiara nel suo `:root`
(0,1,0), qualunque sia l'ordine di caricamento.

**Quindi i colori scritti nel `:root` di `frontend/src/styles.css` non sono
quelli che si vedono nel browser.** L'identita' viva e': carta `--n-50`, inchiostro
`--n-900`, accento corallo `--coral-500`, rampa dati teal `--seq-1..6`, font
**Newsreader / Public Sans / Spline Sans Mono**. Stanno tutti in
`app/static/css/ds/system.css`, che e' l'unico posto dove cambiarli.

Le due shell che montano il bundle dell'atlante (`app.html` e `confronto.html`)
si migrano **insieme**: sono la stessa applicazione React, e se una resta senza
`ds` la stessa vista si vede in due palette a seconda della URL.

Un colore cotto nel foglio (un `rgba(...)` o un hex) non segue il tema scuro:
usare i token, sempre. E' il difetto che teneva il masthead dell'atlante chiaro
mentre il resto della pagina era scuro.

Le pagine ancora sul chrome legacy (`site.css`, il ramo `else` di
`blog_base.html`) restano com'erano finche' non tocca a loro: la migrazione e'
**opt-in per pagina**, con `{% set ds_page = true %}`. Quel ramo e `site.css`
spariranno insieme, col commit che migra l'ultima pagina.

La SPA non conosce le rotte Flask: una vista path-scoped si monta con
`window.__diInitialView` dal template, mai insegnando gli URL del server a
`frontend/src/main.jsx`.
