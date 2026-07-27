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

Identita' cartografica, da non diluire (`frontend/src/styles.css`,
`app/static/css/site.css`): navy `#15233b`, carta `#fbfaf7`, un solo accento
`#e4572e`, font Archivo / Inter / Space Mono.

La SPA non conosce le rotte Flask: una vista path-scoped si monta con
`window.__diInitialView` dal template, mai insegnando gli URL del server a
`frontend/src/main.jsx`.
