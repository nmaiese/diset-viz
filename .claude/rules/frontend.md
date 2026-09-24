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
account) lo caricano tutte, shell della SPA comprese.

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
- **l'accento e' dell'interfaccia**, non un colore dei dati. Venti barre tutte
  arancio lo svalutano dove serve: la serie di contesto e' `--cmp-*`, l'accento
  resta all'elemento in evidenza. E una serie non si dipinge col colore del
  testo.

La SPA non conosce le rotte Flask: una vista path-scoped si monta con
`window.__diInitialView` dal template, mai insegnando gli URL del server a
`frontend/src/main.jsx`. E' l'unica cosa che la pagina le passa: la
navigazione (`window.__diNav`) non le arriva piu', testata, briciole e piede
(`_ds_footer.html`) li rende Flask fuori da `#root`.

Nel CSS della SPA si usano solo i nomi che `body.ds` ripunta (`--ink`,
`--paper`, `--muted` e simili). Un token ricavato sulla radice della 1.0
(`--surface-inverse`, `--text-*`) nella SPA non esiste o vale il ripiego, e il
colore esce sbagliato senza che niente fallisca.
