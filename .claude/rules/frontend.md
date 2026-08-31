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

## Un solo sistema grafico

L'identita' del sito e' il **design system 2026**, e sta tutta in
`app/static/css/ds/system.css`: carta `--n-50`, inchiostro `--n-900`, accento
corallo `--coral-500`, rampa dati teal `--seq-1..6`, font **Newsreader /
Public Sans / Spline Sans Mono**. E' l'unico posto dove si cambia un colore.

L'atlante e il confronto (`app/templates/app.html`, `app/templates/confronto.html`)
caricano quel foglio e mettono `class="ds"` sul body: da li' `body.ds`
(specificita' 0,1,1) ripunta i token che `frontend/src/styles.css` dichiara nel
suo `:root` (0,1,0). **Quindi i colori scritti in quel `:root` non sono quelli
che si vedono**: sono il ripiego per quando il foglio del design system non c'e'.

Le due shell si migrano e si toccano **insieme**: sono la stessa applicazione
React, e se una resta indietro la stessa vista si vede in due palette a seconda
della URL.

Due errori che non fanno fallire niente:

- **un colore cotto** (un hex o un `rgba()`) non segue il tema scuro. E' il
  difetto che teneva il masthead dell'atlante chiaro con la pagina scura, e la
  mappa sulla rampa chiara. In JS un `var()` non si risolve in un attributo di
  presentazione (`fill=`): va messo in `style`.
- **il corallo e' l'accento dell'interfaccia**, non un colore dei dati. Venti
  barre tutte coralli lo svalutano dove serve: la serie di contesto e'
  `--cmp-*`, il corallo resta all'elemento in evidenza. E una serie non si
  dipinge col colore del testo.

La SPA non conosce le rotte Flask: una vista path-scoped si monta con
`window.__diInitialView` dal template, mai insegnando gli URL del server a
`frontend/src/main.jsx`.
