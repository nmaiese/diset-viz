# Riconciliazione fra le due proposte di pipeline editoriale

Scritto da Antigravity (`gemini-3.1-pro-high`, headless), a partire dalle due proposte:
`docs/design_drafts/pipeline_indicatori_PROPOSTA.md` (Codex) e
`docs/design_drafts/pipeline_blog_PROPOSTA.md` (Claude). Letto per intero da Nello e Claude
coordinatore, non modificato rispetto all'output originale.

## 1. Pattern e casi reali di pipeline editoriali automatizzate con LLM

L'integrazione dei Large Language Models (LLM) nel data journalism si sta consolidando attorno ad architetture difensive, modulari e rigidamente strutturate ("human-in-the-loop"). Lo standard di settore non prevede l'automazione end-to-end della pubblicazione, ma l'uso dei modelli come "force multiplier" per compiti di riassunto, strutturazione o stesura di bozze basate su dati deterministici.

- **Data journalism automation e AI Newsroom**: la prassi prevede di confinare i LLM alla sola fase di generazione linguistica, bloccando l'accesso diretto alla rete durante la scrittura per evitare la fabbricazione di link o fonti. Il processo di ingestione dei dati grezzi, il calcolo delle variazioni e la creazione di un dossier JSON/YAML rimangono di competenza esclusiva di script deterministici. Un esempio noto è quello dell'Associated Press, che genera resoconti sui trimestrali di cassa incrociando i dati finanziari con template supervisionati dai giornalisti ([Automated earnings stories multiply - AP](https://www.ap.org/the-definitive-source/announcements/automated-earnings-stories-multiply/)). Pattern analoghi per disaccoppiare la "plumbing" dei dati dal giudizio editoriale sono discussi nei framework operativi per le redazioni moderne ([Generative AI Newsroom](https://generative-ai-newsroom.com/)).
- **Fact-checking gates per contenuti LLM**: poiché i modelli linguistici sono macchine probabilistiche e non database di verità, le pipeline affidabili introducono gate deterministici: un post-processore software intercetta il testo generato e verifica che ogni cifra, claim o URL citato corrisponda in modo identico a un dizionario di verità pre-fornito (il dossier o il corpus fonti). Nessun contenuto supera il gate senza l'uguaglianza dei supporti probatori, e il passo finale di validazione resta umano.

## 2. Confronto tra le proposte: sovrapposizioni e conflitti reali

- **Corpus fonti condiviso**: sovrapposizione forte e rischio strutturale. Entrambe le pipeline fanno riferimento allo stesso universo di enti istituzionali (Istat, Inail, Openpolis, ecc.) per l'estrazione di affermazioni verificabili verbatim. La proposta blog ipotizza un registro proprio. Se le due pipeline mantengono directory separate per il corpus e i claim, si incorre in duplicazione della verità, divergenza silenziosa degli URL e onere doppio di aggiornamento.
- **Nomi in `app/sources.py`**: la pipeline indicatori richiede esplicitamente che ogni etichetta e URL passi dal registro interno del sito. Il blog propone di ripristinare script come `collect.py` o `photo.py`. Se questi moduli vengono riparati isolatamente senza agganciarsi al vocabolario di `sources.py`, le due sezioni del sito presenteranno citazioni disallineate o link divergenti per le medesime fonti primarie.
- **Criterio di `editorial_state`**: conflitto di design. La pipeline indicatori è ancorata a `app/editorial_state.py` come unica fonte di verità sullo stato della coda. La pipeline blog ignora questo stato e si innesca da `config/trend_topics.json` e trigger esterni. Scopi diversi, ma l'assenza di un punto di contatto rischia di oscurare nel cruscotto di progetto il lavoro del blog.
- **Voce e `content/STYLE.md`**: entrambe promuovono `STYLE.md` a fonte unica di verità normativa. Se due agenti indipendenti (blog-writer e scrittore indicatori) ricevono prompt di contorno molto diversi, la voce unitaria del sito rischia di spezzarsi.
- **Limite di 8 pagine a settimana**: conflitto operativo più grave. Entrambe le proposte citano il vincolo, ma sono due lavoratori asincroni che non si vedono: senza un contatore condiviso la somma delle pubblicazioni concorrenti sforerà il tetto.
- **Dove vive il codice**: entrambe rivendicano la permanenza dentro Divario Italia, scartando i repository della vecchia redazione (il documento blog nomina `nmaiese/redazione-ai` in un punto, in contraddizione con la propria stessa regola: vedi revisione GLM in `pipeline_blog_review_free_models.md`). La prossimità è diversa: indicatori agisce a contatto con `app/`, il blog resta uno script di servizio con dipendenze da bonificare.

## 3. Raccomandazione netta: cosa condividere e cosa separare

**Condividere, senza eccezioni:**
1. **Corpus e catalogo fonti** (`data/corpus/`, `app/sources.py`): un solo registro istituzionale, letto da entrambe le pipeline per le citazioni verbatim e la risoluzione URL.
2. **Contatore di throughput condiviso**: il tetto di 8 pagine/settimana va centralizzato (adiacente a `editorial_state.py`), interrogato da entrambe le pipeline prima di proporre una PR.
3. **Motore dei gate numerici deterministici**: la logica che verifica "una cifra nel testo corrisponde a una cifra nel dossier" deve poggiare su una libreria comune, non su due implementazioni con arrotondamenti divergenti.

**Tenere separato:**
1. **Trigger, coda e costruzione del dossier**: indicatori è state-driven (CSV Istat), blog è event-driven (trend, RSS). Restano pipeline indipendenti.
2. **Agenti LLM, system prompt e ruoli**: lo scrittore indicatori è un tecnico che sostituisce parametricamente prosa passata; il blog-writer lega un fatto di trend a titolazione e immagine. Un solo agente per entrambi produrrebbe un prompt fragile.
3. **Ambiente di esecuzione**: librerie instabili o non essenziali alla generazione statica (`pytrends`, `requests` al posto di `urllib`) restano fuori da `requirements.txt` di produzione, isolate in un requirements di sviluppo per gli step di raccolta del blog.
