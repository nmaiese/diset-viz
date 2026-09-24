---
paths:
  - "design/**"
---

# Design della 1.0

`design/` contiene il progetto della versione 1.0: il sistema di pagina
(`design/v1/SISTEMA.md`), i token della direzione "Cronaca"
(`design/v1/tokens/tokens.json`) e i prototipi statici con dati veri.

- **E' il cantiere, il sito e' in `app/`.** La 1.0 e' in produzione: i token
  stanno in `app/static/css/ds/system.css`, i componenti in
  `app/static/css/ds/components.css`, le macro in `app/templates/v1/_ui.html`,
  le pagine in `app/templates/v1/` e cio' che chiedono ai dati in `app/design/`.
  Un prototipo che cambia qui non cambia il sito: si porta in `app/` con una
  PR, e i due vanno tenuti allineati a mano. Il codice di `app/` non legge
  niente da `design/`, che non entra nell'immagine di Cloud Run
  (`tests/unit/test_design_runtime.py`).
- Un colore si cambia in `tokens.json` e si rigenera `tokens.css` con
  `tools/tokens.py`, poi si riporta in `app/static/css/ds/system.css`. Il CSS
  dei componenti legge solo token: niente esadecimali, niente `rgba()`.
- Nessuna cifra dei prototipi si scrive a mano: arriva dal contesto catturato
  (`tools/extract.py`) o da una funzione dell'app (`tools/derive.py`). Quella che
  non si puo' calcolare resta un segnaposto visibile.
- Valgono le regole del testo visibile di `content/STYLE.md` (niente trattino
  lungo o medio, punto e virgola, puntini) e `tools/check_pages.py` le controlla.
- Gli screenshot si fanno con `tools/shots.mjs` e Chrome headless via CDP, con
  `Emulation.setDeviceMetricsOverride`: `--window-size` sotto i 500px mente.
  Chrome non disegna dentro la sandbox di Claude Code.
