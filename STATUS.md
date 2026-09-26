# STATUS — Divario Italia

Stato corrente, architettura, obiettivi e roadmap locale di **Divario Italia** (`divarioitalia.it`).
Questo documento è l'unica sorgente di verità per lo stato di questo progetto (completamente autonomo e isolato dagli altri siti).

---

## 1. Identità e Infrastruttura del Progetto

* **Repository / Path locale**: `~/dev/sites/divarioitalia` (con symlink legacy `~/dev/sites/diset-viz`)
* **URL Produzione**: `https://divarioitalia.it`
* **Hosting**: Google Cloud Run (servizio `diset-viz`, regione `europe-west1`, progetto GCP `nil-automata`)
* **Deploy**: Container Docker compilato via Google Cloud Build su push/merge
* **Edge / CDN**: Cloudflare (proxy DNS, SSL, caching edge)
* **Database**: Supabase Postgres (gestito con migrazioni Alembic in `alembic/`)
* **Analytics / Ads**:
  * Google Tag Manager: `GTM-PZ45BG7D`
  * GA4 Measurement ID: `G-THTPZZ02QH`
  * AdSense Client: `ca-pub-6806451730012282`
* **Credenziali di Servizio**:
  * Service Account GA4 / Search Console: `~/.config/gcloud/ga4-mcp-sa.json` (`ga4-mcp@nil-automata.iam.gserviceaccount.com`)
  * GCloud account: `maiese.next@gmail.com`

---

## 2. Architettura Applicativa

* **Framework**: Python Flask, servito da gunicorn.
* **Interprete**: `bin/py` (risolve l'ambiente virtuale corretto con le dipendenze).
* **Frontend**:
  * Design System 1.0 "Cronaca" (palette monocromatica `#121519`, accento arancio `#a75001`, rampa dati blu, Sofia Sans self-hosted in `app/static/css/ds/system.css`).
  * Pagine servite interamente server-side da `app/templates/v1/` con view models dedicati (`app/design/`).
  * React (`frontend/`, compilato via Vite in `app/static/dist/`) è limitato al modulo interattivo `/quiz`.
  * Header, tema e login gestiti in Vanilla JS (`site.js`).
* **Dati**:
  * 634 indicatori territoriali ufficiali Istat/BES (107 province, 20 regioni).
  * Dataset in `app/static/data/Assoluti_Regione.csv`, caricato e cachato in memoria (`lru_cache`).
* **Pipeline Editoriale**:
  * I contenuti attuali risiedono in `content/indicators/*.md` e `content/posts/*.md`.
  * La vecchia catena esterna è dismessa; qualsiasi futura pipeline verrà progettata e implementata da zero in modo autonomo.

---

## 3. Comandi Essenziali

```bash
# Esecuzione test unitari (<1s)
bin/py -m unittest discover -s tests/unit -v

# Esecuzione suite completa (unit + integration Flask/HTTP)
bin/py -m unittest discover -s tests -v

# Build frontend / quiz (se si tocca frontend/src)
cd frontend && npm run build && cd ..

# Server locale
.venv/bin/gunicorn run:app -b 127.0.0.1:5050
```

---

## 4. Stato dei Lavori (Attivo)

### Completati di recente:
- [x] Riorganizzazione workspace: cartella rinominata da `diset-viz` a `divarioitalia` con symlink per retrocompatibilità.
- [x] Registrazione del repository `divarioitalia` in Orca (ID `d2ae0385-1020-40e5-8859-7fbd55a33e03`).
- [x] Separazione totale da repository esterni: hook, regole e documentazione operativa puntano a questo `STATUS.md`; la vecchia pipeline editoriale non viene più invocata.
- [x] Consolidamento dell'aggiornamento UI della home e bersaglio tattile dello spotlight portato ad almeno 44 px.
- [x] Tooling condiviso in `~/dev/ops` con `doctor.sh`, accesso operativo verificato per GCloud, Cloud Run, GCS, GA4, Search Console e Cloudflare.
- [x] Suite completa unit + integration: 1.334 test passati il 26 settembre 2026.

### In Corso / Prossimi:
- [ ] Progettare da zero l'eventuale nuova pipeline editoriale, solo quando tornerà prioritaria rispetto al sito e al runtime.
