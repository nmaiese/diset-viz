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
- [x] Rilascio della PR `nmaiese/diset-viz#279` verificato in produzione il 26 settembre: titoli di regioni e province, redirect legacy con query, `page_type` e suggerimenti delle strisce sono live.
- [x] Verifica tecnica post-rilascio: sitemap canonica reinviata in Search Console il 25 settembre, 573 URL, zero errori e zero avvisi. Home, `ter-12` e `/provincia/milano` risultano indicizzate, con fetch e canonical corretti.
- [x] Il 403 incontrato da GSC Wizard non e' piu' riproducibile: GSC Wizard, Googlebot e Bingbot ricevono HTTP 200. La procedura circoscritta per eventuali ricorrenze resta in `DEPLOY.md`.
- [x] Le 107 pagine provincia hanno titoli, descrizioni e sintesi distintive derivate dai dati verificati. Le decisioni su H1 regionali e tre tagli responsive della striscia sono recepite nel sistema corrente.

### In Corso / Prossimi:
- [ ] Allineare il container GTM al codice corrente: rimuovere i tag morti `back_to_atlas`, `select_sibling_indicator` e `change_visualization`; aggiungere i tag mancanti per atlante e confronto; limitare i tag di produzione all'hostname `divarioitalia.it`.
- [ ] In GA4 verificare dalla UI la regola per il traffico interno e il relativo filtro dati, registrare solo dimensioni e metriche utili ancora mancanti e annotare il rilascio del 26 settembre. Il dettaglio verificato e' in `docs/tracking_spec.md`.
- [ ] Correggere l'apertura di `content/indicators/13.md`: la pagina misura il tasso di occupazione totale, mentre il lead apre sul solo tasso femminile. `ter-12` non richiede la stessa riscrittura.
- [ ] Verificare in Bing Webmaster Tools lo stato della sitemap. Search Console e' gia' verificata e non richiede un nuovo invio.
- [ ] Decidere se bloccare `Google-Extended` per rendere la regola di `robots.txt` pienamente coerente con `ai-train=no`.
- [ ] Il 24 ottobre 2026 misurare il primo periodo post-rilascio: click, impression, CTR e posizione GSC; sessioni organiche GA4; distribuzione di `page_type`; eventi di atlante, confronto e quiz; traffico di test e `(not set)`; CTR delle pagine regione e provincia.
- [ ] Progettare da zero l'eventuale nuova pipeline editoriale, solo quando tornerà prioritaria rispetto al sito e al runtime.
