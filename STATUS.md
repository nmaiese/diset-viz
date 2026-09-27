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
- [x] Il 27 settembre 2026 il follow-up di `content/indicators/13.md` e' corretto nel ramo `nmaiese/lead-ter-13`, commit `4ef87664`: il lead apre sul tasso di occupazione totale, che e' la misura della pagina, e tiene il divario di genere come angolo. Verificato con 412 test unitari e i 21 test di testo, link interni e prosa. **Non e' fuso**: `content/` passa da PR e il merge e' la pubblicazione. L'audit del catalogo dice che un solo articolo su 383 ha un link a un indicatore nel lead, ed e' questo: il difetto non era sistemico.
- [x] Il 27 settembre 2026 il protocollo multi-agente e' stato corretto invece di duplicato: `docs/WORKFLOW_ORCA.md` ora registra i 49 guasti ricorrenti che avevano prodotto (40 agenti fuori dal proprio worktree, e 9 minori: un `sed -i` fuori worktree, un traceback, due `ruff` per import non ordinati), la regola che ne segue, il fatto che in WSL `orca` e' il lettore di schermo GNOME e il binario e' quello di `ORCA_CLI_COMMAND`, l'obbligo di aspettare `tui-idle` prima di inviare un prompt, e i due difetti della CLI incontrati (creazione che risponde `runtime_unavailable` avendo gia' creato il worktree, e metadati esterni su filesystem che in un caso e' risultato temporaneamente in sola lettura). Il conteggio e' stato ricontrollato sui dati il 27 settembre: la prima versione del documento diceva 41 e 39, e non tornava.
- [x] Il 27 settembre 2026 la voce delle 388 schede indicatore e' stata misurata, e la misura dice che il 46,2% di testo ripetuto **non e' un difetto**: e' consistenza. Nel dettaglio in `docs/AUDIT_VOCE.md`. Le cifre che si ripetono sono anni e l'esempio illustrativo del metodo, mai il valore di una regione; i blocchi «come leggere» sono 261 varianti su 388 pagine, 197 con l'esempio della percentuale e 191 con un altro, e il «limite principale» e' specifico per indicatore. Il percorso per arrivarci ha corretto due errori miei: una conclusione («nessun numero condiviso») che il dato non reggeva, e un controllo che filtrava le cifre dopo aver preso solo le prime sei sequenze, quindi non era mai stato eseguito.

### In Corso / Prossimi:
- [ ] **Ramo `nmaiese/lead-ter-13` da guardare e da fondere**: una riga di `content/indicators/13.md`, commit `4ef87664`, worktree Orca `lead-ter-13` in `in-review`. Finisce qui: push e PR restano a Nello.
- [ ] Allineare il container GTM al codice corrente. La lista esatta e' gia' contata sul codice il 27 settembre e sta in `docs/tracking_spec.md`: da rimuovere `back_to_atlas`, `select_sibling_indicator`, `change_visualization`; da creare `compare_select_indicator`, `open_region`, `open_province`, `filter_macro_area`, `filter_data_source`, `filter_year_range`; e la condizione hostname `divarioitalia.it` va messa sul trigger `CE - page_view`. Resta lavoro di UI, non di codice.
- [ ] Capire se `POST /api/events` e' un canale di debug utilizzabile: scrive `analytics_event` con `app.logger.info`, ma il 27 settembre una ricerca nei log di Cloud Run del servizio `diset-viz` con `--freshness=7d` non ha trovato nulla, e non e' chiaro se per assenza di interazioni o per il campo in cui gunicorn lascia le righe dell'app. Finche' non e' chiaro, il canale non si usa come dato di fatto.
- [ ] In GA4 verificare dalla UI la regola per il traffico interno e il relativo filtro dati, registrare solo dimensioni e metriche utili ancora mancanti e annotare il rilascio del 26 settembre. Il dettaglio verificato e' in `docs/tracking_spec.md`.
- [ ] Verificare in Bing Webmaster Tools lo stato della sitemap. Search Console e' gia' verificata e non richiede un nuovo invio.
- [ ] Decidere se si prova la variazione della voce su **una** scheda. `docs/AUDIT_VOCE.md` chiude il rischio di contenuto duplicato e lascia aperta la sola perplessita' di percezione: quattro frasi-telaio si ripetono su 388 pagine. La raccomandazione, che arriva anche dai due provider free chiesti separatamente, non e' di riscrivere tutto, ma di costruire una variante su un indicatore, misurarla, e decidere poi. Serve un indicatore scelto da Nello e una metrica di lettura.
- [ ] Correggere il nome e il docstring di `scripts/duplicazione.py`, che dicono «testo identico» mentre non distinguono una sequenza di dati da una di raccordo, e farlo riportare **le due quote**, con e senza numeri, piu' quante sequenze condivise contengono una cifra. E' la riga che avrebbe reso l'audit di stanotte leggibile al primo colpo. Cambia `scripts/` e `tests/`, quindi passa da PR.
- [ ] Decidere la politica sui crawler AI, ora che e' pronta per essere decisa. La domanda "bloccare `Google-Extended` per coerenza con `ai-train=no`" ha una risposta che la contraddice, perche' quel token governa insieme addestramento e grounding: bloccarlo tiene lontano Gemini dall'addestramento e toglie il sito dalle risposte grounded, cioe' da `ai-input=yes`. Fonti e alternative in `docs/AI_CRAWLERS.md`; la scelta resta di Nello.
- [ ] Il 24 ottobre 2026 misurare il primo periodo post-rilascio: click, impression, CTR e posizione GSC; sessioni organiche GA4; distribuzione di `page_type`; eventi di atlante, confronto e quiz; traffico di test e `(not set)`; CTR delle pagine regione e provincia.
- [ ] Ripulire il relitto `wf_51e801ac-d39-1` in `.claude/worktrees/` (111M): il ramo `claude/atlante-modulo-api` e' gia' dentro `master`, quindi il lavoro e' merged e il worktree non serve piu'. Serve un ok, perche' cancellare rami e' decisione di Nello.
- [ ] Progettare da zero l'eventuale nuova pipeline editoriale, solo quando tornerà prioritaria rispetto al sito e al runtime.
