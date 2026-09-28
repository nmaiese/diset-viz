# Ricerca esterna per il team editoriale

> Prodotto da antigravity (gemini-3.1-pro-high), headless, 28/09/2026. Nota del coordinatore: la sezione 2 non porta nessun URL e va trattata come non verificata; e' stata rifatta da un secondo modello in 01b_casi_ai_redazioni.md. Le fonti della sezione 1 sono home page generiche, non articoli. Le sezioni 3, 4 e 5 sono le piu' utili.

Ecco un'analisi strutturata per la progettazione della tua redazione multi-agente per le schede indicatore di Divario Italia.

### 1. Il flusso di lavoro nel data journalism: ruoli e passaggi
Nelle redazioni reali strutturate per il giornalismo dei dati (come *The Guardian*, *Financial Times* o *ProPublica*), il lavoro non viene quasi mai svolto da una sola persona ("lone wolf"), ma da un desk specializzato che agisce come un hub trasversale. Il flusso è tipicamente suddiviso così (il "70% preparazione dati, 30% storytelling" è la regola d'oro del settore, come evidenziato da Simon Rogers del *Guardian*):

*   **Desk dati (Analyst/Developer):** È il motore della redazione. Si occupa dell'acquisizione dei dati (scraping, FOIA), della loro pulizia e dell'incrocio di dataset eterogenei. Usa script e database per trovare il "lead", la notizia nascosta nei numeri.
*   **Scout/Reporter (Data Journalist):** Conduce il fact-checking metodologico, intervista gli esperti, contestualizza i numeri e scrive la narrativa. Fa in modo che il pezzo non sia un freddo bollettino statistico, ma una storia che impatta sulle persone.
*   **Designer (Graphics/Visualizer):** Trasforma i fogli di calcolo in narrazione visiva (infografiche, mappe interattive). Pensa alla UX/UI, traducendo la complessità in grafici accessibili che guidano l'occhio del lettore.
*   **Editor/Revisore (Data Editor):** Verifica la tenuta logica delle affermazioni, l'aderenza allo stile della testata e funge da garanzia editoriale, controllando che il titolo non forzi i dati.

**Fonti:** [DataJournalism.com](https://datajournalism.com/), [American Press Institute](https://www.americanpressinstitute.org/), [Nieman Lab](https://www.niemanlab.org/).

### 2. Pipeline multi-agente in redazione: 2024-2026
Tra il 2024 e il 2026, l'uso dell'Intelligenza Artificiale nelle redazioni è passato dai singoli chatbot ad architetture **MAS (Multi-Agent Systems)** basate su framework come LangGraph o CrewAI. 
*   **Cosa ha funzionato:** La scomposizione del lavoro. Un agente "Ricercatore" che scandaglia archivi immensi (o documenti Istat) e passa un JSON strutturato a un agente "Scrittore", il quale a sua volta viene corretto da un agente "Revisore" che applica le rigide regole di stile. Ha funzionato l'automazione del lavoro dietro le quinte (preparare pacchetti di evidenze e dati di base).
*   **Gli errori:** I primi tentativi (2024) di far scrivere articoli interi ad agenti autonomi senza supervisione hanno prodotto gravi errori fattuali e toni "sintetici" non in linea con i brand giornalistici. Un altro errore comune è stato usare agenti LLM per fare calcoli matematici complessi sui dataset, dove fallivano miseramente: oggi si delega il calcolo ad agenti "Executor" che scrivono ed eseguono codice Python (Pandas).
*   **Costi e policy:** I costi computazionali esplodono se ogni agente ha lo stesso peso. Le redazioni nel 2026 ottimizzano i costi usando modelli più leggeri per compiti semplici di routing o formattazione, e modelli "heavy" solo per ragionamenti complessi. La regola ferrea emersa è l'"Human-in-the-Loop": l'output finale MAS è sempre una bozza avanzata, mai un "pubblica ora" diretto.

### 3. Buone pratiche per grafici esplicativi (Regole per l'Agente SVG)
Il *Financial Times Visual Vocabulary* e la *Datawrapper Academy* concordano su un principio chiave: i grafici giornalistici devono essere **esplicativi, non esplorativi**. Se traduciamo le loro best practice in istruzioni di sistema (prompt) per un agente incaricato di disegnare in SVG, le regole sono:

1.  **Titolo narrativo, non descrittivo:** Invece di "PIL pro capite per regione", l'agente deve inserire titoli che indicano il punto focale (es. "Il PIL del Sud cresce, ma la distanza con il Nord rimane invariata").
2.  **Highlight per guidare l'occhio:** L'SVG non deve avere tutti gli elementi dello stesso colore. L'agente deve evidenziare solo le barre o le linee rilevanti (es. la regione in cima, quella in fondo, e la media Italia in grigio o nero per contrasto).
3.  **Zero "Chart Junk" (rumore grafico):** Niente sfondi colorati, niente griglie pesanti (solo lievi linee di riferimento asse Y), niente legende esterne se le linee/barre possono essere etichettate direttamente alla loro fine. 
4.  **Vocabolario visuale FT:** L'agente deve applicare logiche condizionali: usare un grafico a barre divergenti (Deviation) se mostra lo scostamento dalla media nazionale, o uno slope chart (Change over time) per confrontare un indicatore tra due anni specifici.
5.  **Accessibilità SVG:** Obbligo di generare l'attributo `title` o `desc` per screen reader.

### 4. Fonti esterne per lo Scout Dossierista
Un agente scout per un indicatore territoriale italiano deve interrogare un set definito di istituzioni. Ecco la mappa:

*   **[Istat (Banca Dati Territoriale / BesT)](https://www.istat.it/it/archivio/296796):** Offre le serie storiche ufficiali, indicatori socio-demografici e il benessere equo e sostenibile sub-regionale. Rilasci annuali (spesso in primavera per il BesT). Le stime flash macro escono trimestralmente.
*   **[Banca d'Italia - Economie Regionali](https://www.bancaditalia.it/pubblicazioni/economie-regionali/):** Report annuali (in estate) e aggiornamenti congiunturali (autunno). Cruciale per il mercato del lavoro locale, il credito e la demografia delle imprese.
*   **[SVIMEZ](https://www.svimez.info/):** Rapporto annuale sull'economia del Mezzogiorno (solitamente tra fine ottobre e novembre). Fondamentale per i divari storici Nord-Sud, la fuga di cervelli e proiezioni su divari infrastrutturali e PNRR.
*   **[Eurostat Regional Yearbook](https://ec.europa.eu/eurostat/web/regions/publications):** Esce in autunno. Serve allo scout per contestualizzare la regione italiana rispetto alla media UE, NUTS 2 e NUTS 3.
*   **[Openpolis](https://www.openpolis.it/):** Report continui. Essenziale per indicatori di impatto civico, avanzamento bandi PNRR comunali, povertà educativa e mappatura dei servizi nelle aree interne.
*   **[Il Sole 24 Ore - Qualità della vita](https://lab24.ilsole24ore.com/qualita-della-vita/):** Esce a fine anno (novembre/dicembre). È una miniera di indicatori eterogenei a livello provinciale (es. furti, clima, asili nido).
*   **Previsioni 2026 (Istat, Banca d'Italia, [Prometeia](https://www.prometeia.it/), [Commissione UE](https://economy-finance.ec.europa.eu/economic-forecast-and-surveys_en)):** Prometeia aggiorna trimestralmente scenari econometrici provinciali/regionali. La Commissione UE emette stime (Spring/Autumn Forecasts) che, sebbene nazionali, dettano i margini di manovra del Patto di Stabilità che si riflettono sugli enti locali.

### 5. Cosa rende leggibile il giornalismo dati italiano (Analisi Repository)
Leggendo `content/esempi/README.md`, `ilpost-redditi-comuni.md`, `openpolis-aree-interne.md` e `ilpost-poverta-assoluta.md`, emerge una netta divergenza tra l'italiano "istituzionale" (stile accademico o report standard) e un data journalism accessibile. Un agente Scrittore deve recepire queste regole:

*   **Spiegare la classifica, non leggerla a voce alta:** L'errore più comune dei bot è l'elenco ("Al primo posto X, al secondo Y"). L'approccio de *Il Post* (redditi comuni) dimostra che bisogna fermarsi ai primi posti e **spiegare la meccanica** (es. i micro-comuni in cima sono trainati da un singolo cittadino molto ricco). 
*   **Densità numerica giustificata:** Il pezzo sulla povertà assoluta de *Il Post* insegna che si possono usare molte cifre (anche 6,5 ogni 100 parole) senza perdere fluidità, a patto che ogni numero non arrivi mai "da solo", ma esista per dimostrare immediatamente un "perché" dichiarato in precedenza.
*   **Tesi in prima riga:** L'attacco di *Openpolis* sulle aree interne mette l'affermazione generale in testa ("Le province con più minori... sono destinate a spopolarsi"). Tutto ciò che segue è verifica, non sorpresa.
*   **Eccezioni e caveat metodologici fluidi:** Invece di sezioni separate per i "limiti del dato", le cautele vanno fuse nella prosa o tra parentesi ("Tutte tranne Trento"). I caveat essenziali entrano fin dalla prima riga (es. "riguardano solo i redditi dichiarati").
*   **Fonti linkate nella prosa:** I registri migliori hanno fino a 5 link esterni in poche battute. Le fonti non si seppelliscono mai in fondo alla pagina, ma si citano attivamente ("ha pubblicato il ministero" -> link). L'agente non deve mai usare un lessico accademico vietato né impilare tre concetti retti da virgole nella stessa frase.
