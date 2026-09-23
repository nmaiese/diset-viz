---
paths:
  - "design/**"
---

# Design della 1.0

`design/` contiene il progetto della versione 1.0: il sistema di pagina
(`design/v1/SISTEMA.md`), i token della direzione "Cronaca"
(`design/v1/tokens/tokens.json`) e i prototipi statici con dati veri.

- **Non e' l'identita' in vigore.** Il sito legge i colori, i font e le ombre da
  `app/static/css/ds/system.css`, e cosi' resta finche' una PR di migrazione non
  porta i token in `app/`. Copiare un valore da qui a `app/` fuori da quella PR
  e' lo stesso errore della vecchia cartella `design-system/`, che per mesi ha
  descritto un'identita' morta agli agenti che la trovavano.
- Un colore si cambia in `tokens.json` e si rigenera `tokens.css` con
  `tools/tokens.py`. Il CSS dei componenti legge solo token: niente esadecimali,
  niente `rgba()`.
- Nessuna cifra dei prototipi si scrive a mano: arriva dal contesto catturato
  (`tools/extract.py`) o da una funzione dell'app (`tools/derive.py`). Quella che
  non si puo' calcolare resta un segnaposto visibile.
- Valgono le regole del testo visibile di `content/STYLE.md` (niente trattino
  lungo o medio, punto e virgola, puntini) e `tools/check_pages.py` le controlla.
- Gli screenshot si fanno con `tools/shots.mjs` e Chrome headless via CDP, con
  `Emulation.setDeviceMetricsOverride`: `--window-size` sotto i 500px mente.
  Chrome non disegna dentro la sandbox di Claude Code.
