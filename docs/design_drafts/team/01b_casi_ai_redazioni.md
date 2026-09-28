# Casi di redazioni che usano l'AI in una pipeline a più ruoli

Prodotto da Antigravity in headless, modello `gemini-3.1-pro-high`, 28 settembre
2026. Il primo tentativo era affidato a GLM-5.3-Flash, che si è fermato a metà
lavoro per crediti Hugging Face esauriti.

**Verifica del team leader.** Ogni URL è stato aperto con `curl` e ogni
citazione cercata nel testo della pagina.
- **Verificati quattro casi su cinque**: Il Sole 24 Ore, Schibsted, Newsquest
  tramite Nieman Lab, Full Fact. Per ognuno la citazione letterale è presente
  nella pagina.
- **Associated Press**: la pagina risponde 403 a un client senza browser,
  quindi la citazione non è verificata. Il caso resta plausibile ma non
  confermato.

**Da leggere con cautela, le "lezioni" in fondo.** Il modello ha scambiato i
quattro ruoli per persone ("4 esseri umani"), mentre qui sono agenti. Quello che
resta utile, e che il piano applica:
- **Newsquest.** Chi controlla deve confrontare il testo con la fonte, frase per
  frase. È il compito della guardia deterministica e della domanda 4 del
  revisore.
- **Il Sole 24 Ore.** Il modello lavora dentro un perimetro chiuso di fonti
  certificate. È il contratto di `fonti.md`: URL aperto, citazione letterale,
  "non trovato" quando manca.
- **AP.** Niente va online senza un controllo che firma. È il merge di Nello.

---

# Report: Agenti e Modelli AI nelle Redazioni Giornalistiche (2024-2026)

## 1. Il Sole 24 Ore
* **Redazione:** Il Sole 24 Ore (Italia)
* **Pipeline:** Integrazione di "24Ore AI", una nuova generazione di intelligenza artificiale integrata per affiancare la navigazione, con chatbot e ricerca avanzata sulle notizie aziendali, finanziarie e statistiche.
* **Ruoli macchine vs persone:** Il chatbot e il motore di ricerca AI recuperano e sintetizzano le informazioni per i lettori; le persone (i giornalisti) redigono gli articoli, controllano e alimentano il database interno.
* **Controllo umano:** Il controllo è sistemico e a monte. L'AI non è lasciata libera di scansionare il web, ma elabora le sue risposte attingendo esclusivamente al perimetro chiuso e certificato degli articoli e dei dati pre-pubblicati dalla redazione.
* **Cosa ha funzionato / Cosa è andato storto:** Ha funzionato la creazione di un dialogo diretto tra l'utente e i dati finanziari o normativi abbattendo drasticamente le allucinazioni grazie all'impiego esclusivo di fonti interne autorevoli. L'ostacolo principale gestito è il rischio di generare contenuti inaffidabili se il perimetro informativo non viene mantenuto sigillato e aggiornato.
* **URL:** `https://www.professionereporter.eu/2026/06/sole-24-ore-nuova-home-page-i-lettori-domandano-alla-ai-interna/`
* **Data:** 16 Giugno 2026
* **Citazione letterale:** "Con il lancio della nuova home page debutta ufficialmente anche 24Ore AI, la nuova generazione di Intelligenza artificiale sviluppata dal Sole 24 Ore."

## 2. Associated Press (AP)
* **Redazione:** Associated Press (Stati Uniti)
* **Pipeline:** Utilizzo di modelli AI generativi per automatizzare attività redazionali massive e strutturate, focalizzandosi in particolare sulla traduzione degli articoli dall'inglese allo spagnolo e sull'ottimizzazione dei metadati, regolamentati da rigorosi standard interni.
* **Ruoli macchine vs persone:** Il modello AI converte i testi e prepara le prime bozze localizzate o etichettate; i giornalisti e gli editor compiono il reportage originale, revisionano e mantengono il giudizio editoriale finale su ogni parola.
* **Controllo umano:** Il controllo funge da gatekeeper assoluto prima della messa in rete. Nessuna intelligenza artificiale può alterare contenuti multimediali (foto/video) e nessun testo tradotto automaticamente può essere pubblicato senza che un editor lo abbia prima revisionato per assicurarne l'accuratezza.
* **Cosa ha funzionato / Cosa è andato storto:** Ha funzionato l'aumento dell'efficienza per espandere il raggio d'azione del giornalismo in mercati bilingue tramite traduzioni rapide. Tuttavia, l'assenza intrinseca di bussola etica nell'AI si è rivelata una criticità, obbligando l'agenzia a vietare rigorosamente ai propri dipendenti di usare sistemi automatizzati per creare articoli o immagini fotografiche prive del vaglio umano.
* **URL:** `https://www.ap.org/the-definitive-source/behind-the-news/updates-to-generative-ai-standards/`
* **Data:** 2024
* **Citazione letterale:** "Three areas where AP will experiment with generative AI are: Translations of English language AP stories into Spanish: The translations will be based on AP stories and an AI model will be used to convert them to Spanish."

## 3. Schibsted
* **Redazione:** Schibsted (Norvegia / Svezia, editori di VG, Aftonbladet, E24)
* **Pipeline:** Creazione di un ecosistema e di un hub AI per sviluppare strumenti proprietari volti a eliminare il lavoro puramente meccanico: tool di trascrizione audio ("JoJo"), generazione di script da testi giornalistici (es. per TikTok) e ottimizzazione delle headline in chiave SEO.
* **Ruoli macchine vs persone:** Le macchine gestiscono la parte amministrativa e formale (trascrizioni, suggerimenti per i titoli, correzioni automatiche delle bozze); i reporter e i capi progetto (come il Director of Editorial AI) governano la creatività, stabiliscono la direzione giornalistica e gestiscono l'ideazione.
* **Controllo umano:** Il controllo avviene decentralizzato nelle mani dei giornalisti stessi, formati per costruire, gestire e revisionare i tool che loro stessi usano, in modo da avere piena comprensione del potenziale e dei limiti tecnici.
* **Cosa ha funzionato / Cosa è andato storto:** Il successo principale è logistico ed economico: il solo strumento di trascrizione ha salvato oltre 18.000 ore di lavoro umano. L'elemento problematico (affrontato internamente) è stata la naturale resistenza o il potenziale abuso tecnico in assenza di formazione, il che ha reso necessario l'istruzione di tutta la redazione per garantire un uso responsabile.
* **URL:** `https://schibsted.com/news/ai-is-sparking-creativity-in-schibsteds-newsrooms/`
* **Data:** 2 Febbraio 2024
* **Citazione letterale:** "Additionally, we are working on further developing our transcription tool JoJo, which has already saved over 18,000 hours in transcription work,” he says."

## 4. Newsquest
* **Redazione:** Newsquest (Regno Unito)
* **Pipeline:** Impiego intensivo di un CMS potenziato dall'intelligenza artificiale per l'elaborazione di dati strutturati. Una flotta di reporter operanti col sistema AI automatizza la riscrittura di comunicati stampa, bollettini ufficiali e rapporti locali convertendoli in veri articoli per le edizioni regionali.
* **Ruoli macchine vs persone:** Il modello AI redige la prima stesura narrativa partendo dal documento grezzo; i 36 reporter umani agiscono da revisori specializzati che verificano la coerenza del testo rispetto alla fonte originale.
* **Controllo umano:** Il giornalista umano è stato retrocesso (o elevato, a seconda delle prospettive) dalla fase di scrittura alla fase esclusiva di controllo qualità, intervenendo obbligatoriamente su fatti e virgolettati prima dell'autorizzazione per la stampa.
* **Cosa ha funzionato / Cosa è andato storto:** Il sistema ha funzionato per riempire ampi spazi di giornali locali desertificati da tagli al personale e dal crollo pubblicitario, garantendo sopravvivenza editoriale. Quello che suscita gravi dubbi qualitativi è la trasformazione del lavoro giornalistico: se il controllo di qualità è distratto o fallisce, si rischia l'introduzione di errori, trasformando i reporter in passivi correttori di bozze anziché in veri investigatori.
* **URL:** `https://www.niemanlab.org/reading/u-k-newspaper-chain-newsquest-now-employs-36-ai-assisted-reporters/` (Nieman Lab tramite Press Gazette)
* **Data:** 2 Aprile 2025
* **Citazione letterale:** "The reporters use an Al-powered CMS to rewrite press releases into stories, and are tasked with checking the facts and quotes are correct in the output..."

## 5. Full Fact
* **Redazione:** Full Fact (Regno Unito)
* **Pipeline:** Sviluppo e utilizzo di infrastrutture automatizzate di fact-checking politico e sociale basate su AI in grado di scandagliare in tempo reale il dibattito pubblico e isolare le affermazioni misurabili rispetto al rumore online.
* **Ruoli macchine vs persone:** Le macchine funzionano come setacci che smistano e isolano claim e dati sospetti nel caos dell'informazione continua; le persone (analisti ed esperti di dati) conducono l'indagine statistica per smentire falsità o fornire il vero contesto.
* **Controllo umano:** Rigoroso e inappellabile. Nessun debunking viene generato e immesso al pubblico direttamente dalla macchina; il fact-checking finale sulle policy o sulla salute pubblica viene firmato ed emanato solo dai professionisti.
* **Cosa ha funzionato / Cosa è andato storto:** Ha funzionato la scalabilità: la capacità dell'AI ha permesso di processare volumi immensi di dati a favore di organizzazioni giornalistiche in oltre 20 Paesi. Il problema enorme (evidenziato nel rapporto stesso) è che l'AI generativa crea disinformazione a un ritmo più veloce di quanto persino i sistemi di fact-checking basati sull'AI riescano a smaltire, portando una guerra asimmetrica.
* **URL:** `https://fullfact.org/policy/reports/full-fact-report-2024/`
* **Data:** 2024
* **Citazione letterale:** "AI can be an enormous force for good, and Full Fact has used it to build automated fact checking tools for fact checkers and journalists in more than 20 countries, helping them separate checkable fact from opinion in the torrent of information online."

---

## Lezioni per una Redazione di Schede Statistiche Regionali

Con un **Team Leader (Claude)** e 4 esseri umani: **Scout**, **Scrittore**, **Grafico**, **Revisore**.

1. **Lo Scout (Ispirato a Full Fact): L'AI come setaccio, ma la verifica dei numeri è umana**
   Esattamente come le AI di Full Fact setacciano il torrente di informazioni pubbliche per intercettare i claim verificabili, lo *Scout* della redazione statistica deve usare le reti per scovare i bollettini ISTAT o regionali più aggiornati. Il Team Leader Claude può processare enormi PDF per individuare le tabelle rilevanti in pochi secondi, ma lo Scout non può mai delegare la lettura primaria: deve accertarsi che il set di dati di origine scaricato (es. bilanci sanitari regionali) sia genuino prima di immetterlo nel ciclo produttivo.
2. **Lo Scrittore (Ispirato a Newsquest): Dalla fatica della stesura al ruolo di "editor dei fatti"**
   Prendendo spunto dalle dinamiche di Newsquest, lo *Scrittore* non deve più consumare ore a convertire aride tabelle percentuali in prosa. Claude si incaricherà della "prima stesura", tramutando i dati grezzi estratti dallo Scout in una scheda discorsiva. Il lavoro umano cambia radicalmente: lo Scrittore si concentra sul colorare il testo con il contesto locale che il modello non conosce e indaga maniacalmente eventuali allucinazioni in cui Claude potrebbe aver invertito un calo percentuale in un aumento.
3. **Il Grafico (Ispirato a Schibsted): Automatizzare il layout per liberare l'intuizione visiva**
   Così come Schibsted sfrutta l'AI per i task strutturali (es. i layout per TikTok), Claude assisterà il *Grafico* scrivendo il codice (ad esempio librerie D3.js o Python) per generare i grafici di base a partire dai CSV forniti. Il grande vantaggio è nel tempo risparmiato, che il Grafico umano userà per compiere le scelte che richiedono reale sensibilità visiva ed empatia: enfatizzare il dato chiave della disoccupazione giovanile e garantire la piena leggibilità (accessibilità e colorimetria) del prodotto finito per i lettori locali.
4. **Il Revisore (Ispirato ad AP): Il gatekeeper che detiene la responsabilità etica**
   Come dettato severamente dalle policy di Associated Press per le traduzioni, nessun testo strutturato da Claude andrà online in automatico. Il *Revisore* agisce come barriera finale: deve validare le schede prodotte, assicurando che nessuna statistica economica e nessuna infografica regionale venga diffusa senza il vaglio etico. Claude calcola, l'umano firma e si assume la responsabilità editoriale della pubblicazione.
5. **Il Team Leader Claude (Ispirato a Il Sole 24 Ore): Un direttore d'orchestra rigorosamente "recintato"**
   Per evitare che inventi dati inesistenti su province italiane sconosciute, il Team Leader Claude deve operare in una modalità ad architettura chiusa, lo stesso principio vitale di 24Ore AI. Claude assegna il lavoro allo Scrittore e al Grafico unicamente sulla base dei documenti (i CSV regionali o i report originali) procurati dallo Scout. L'orchestra funziona proprio perché il Team Leader AI coordina la produzione operando esclusivamente dentro i recinti di realtà verificati dalla redazione.
