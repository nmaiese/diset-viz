# Revisione avversaria delle due proposte, con modelli gratuiti

Due modelli senza costo (quota free/starter), scelti per ridondanza su provider diversi,
hanno riletto `pipeline_indicatori_PROPOSTA.md` e `pipeline_blog_PROPOSTA.md` cercando fonti
inventate, stime irrealistiche, contraddizioni e assunzioni non dichiarate. Nessuno dei due ha
scritto file: revisione testuale, headless, `opencode run -m`.

## `ollama-cloud/gpt-oss:120b`

- **Fonti "inventate" o non verificabili**
  - Entrambi i documenti citano `content/STYLE.md` come riferimento definitivo, ma non è chiaro se copra davvero tutte le regole richieste per blog e schede indicatore; manca un link a una versione o checklist di verifica.
  - Il documento blog afferma che la "verifica verbatim automatica sul corpus prima della PR" basta a garantire l'assenza di fonti false, senza indicare tool o schema di hash per il confronto: la verifica resta teorica.
  - La proposta indicatori dice "non inventare fonti, URL, cause, soglie o confronti" ma non indica dove siano custoditi gli URL ufficiali né come vengano risolti.
- **Stime di costo/tempo irrealistiche**
  - $0,0304 a scheda ignora overhead di rete, retry, latenza, logging.
  - "45 min-2 h" per 634 schede in parallelo con 5 processi non considera rate limit o memoria.
  - Il blog dichiara il costo di calcolo "trascurabile" sottovalutando le quote di Google Trends e il costo della CI.
- **Contraddizioni fra i due documenti**
  - Stato della dipendenza `requests`: il blog la dice assente e propone `urllib`, gli indicatori non la menzionano.
  - Limite 8 pagine/settimana: il blog lo impone esplicitamente, gli indicatori non lo riprendono mai nonostante lotti da 25-50.
  - `verify.py`: richiesto in CI dal blog, assente dai comandi di lint/test degli indicatori.
- **Assunzioni non esplicitate**: dipendenze di `scripts/trend_articles/` oltre `requests` (`pytrends`, `pillow`) non verificate; il "dossier" degli indicatori dato per già completo senza dire chi lo aggiorna; provenienza "sempre risolvibile" senza formato dichiarato.
- **Rischi non mitigati**: `pytrends` senza circuit breaker o caching; file singolo per indicatore senza gestione dei conflitti di merge concorrenti.
- **Incoerenza terminologica**: "dossier" (indicatori) vs "dossier.json" (blog), nessuna definizione comune.

## `huggingface/zai-org/GLM-5.3-Flash`

Ha verificato le fonti citate, non solo segnalato il rischio:

- `gpt-5.6-terra` e i prezzi $2/$12: verificati su OpenAI, calcolo aritmetico corretto; nota che 1.200 token "compresi i reasoning" è ottimista con effort `low`.
- Link AP "A leap forward": reale, datato correttamente.
- Link `mediacopilot.ai` citato nel doc blog come "standard AP 2025": la pagina è datata 24 luglio 2026 ed è un blog scritto con IA, non un'autorità primaria; citare direttamente `ap.org`.
- Fatti di repo verificati come corretti: `STYLE.md` rimanda davvero a `REDAZIONE.md`/voce, `editorial_state.py` ha `build_queue()` e `da_scrivere()`, `requests` non è in `requirements.txt`, gli 11 moduli di `scripts/trend_articles/` esistono. **Nessuna fonte inventata trovata.**

**Contraddizione più grave trovata**: il documento blog dichiara di dover vivere dentro Divario Italia e di non nominare il vecchio repo esterno, poi nella sezione fonti nomina `nmaiese/redazione-ai` come luogo dove "un altro worker" avrebbe riprogettato la pipeline indicatori. Contraddizione con se stesso, e con la regola del progetto (STATUS.md: la vecchia catena esterna è dismessa, la nuova pipeline si progetta qui, da zero).

Altre contraddizioni: corpus secondario dato per certo da un documento e aperto dall'altro; vincolo 8 pagine/settimana segnalato solo dal blog; standard AP datato "2026" in un documento e "2025" nell'altro per lo stesso riferimento.

Stime interne incoerenti: 8-15 minuti di revisione umana a scheda quando la checklist avversaria nello stesso documento richiede più tempo di quello dichiarato; 8-12 giornate di sviluppo per un sistema di gate che il documento stesso descrive come complesso quanto un analizzatore di testo; 1 giorno-persona per portare 6 moduli del blog a `urllib` quando il documento stesso ammette che `photo.py` (multipart upload, resize immagini) è il più costoso.

## Che cosa portano queste due revisioni

Confermano, da fonti indipendenti e senza costo, gli stessi tre problemi che la riconciliazione di
Antigravity isola per architettura: **corpus fonti non unificato**, **nessun contatore condiviso
per il tetto di 8 pagine/settimana**, **il documento blog nomina il repo esterno dismesso in un
punto**, in violazione della propria regola e di quella di progetto. Le stime di costo/tempo di
entrambe le proposte vanno riviste prima di qualunque rollout: sono ottimistiche in modo
sistematico, non solo su un punto isolato.
