# Mappa delle domande sui dati territoriali

Questa mappa descrive domande che una persona può rivolgere a un motore di
ricerca o a un assistente. Non è un piano per generare una pagina per ogni
formulazione. Domande equivalenti convergono sulla stessa scheda indicatore
canonica, dove anno, classifica e andamento sono calcolati dal catalogo al
render. La priorità va alle serie recenti con una fonte primaria raggiungibile.

## Come leggere priorità e lacune

- **P1**: dato 2025 o 2026 nel catalogo, copertura regionale e fonte primaria
  Istat verificabile dalla scheda.
- **P2**: serie utile e verificabile, ma ultimo anno meno recente oppure domanda
  che richiede un confronto tra più elementi dell'interfaccia.
- **P3**: richiesta legittima che oggi non può ricevere una risposta completa
  senza nuovi dati, denominatori o un formato di esportazione aggiuntivo.

L'anno indicato è quello richiesto dalla domanda, non una promessa editoriale.
La scheda deve dichiarare l'ultimo anno realmente disponibile e non sostituirlo
con una stima. Le medie territoriali sono semplici e non vanno chiamate medie
nazionali.

## Interfacce per agenti

Le pagine canoniche restano la fonte pubblica da citare. Un client può
richiederne la variante Markdown inviando `Accept: text/markdown`; la risposta
mantiene lo stesso URL canonico e dichiara `Vary: Accept` e `Content-Location`.
La negoziazione è disponibile per home, atlante, catalogo dati, blog e articoli,
metodologia, schede indicatore, profili regionali e temi.

La scoperta automatica parte dagli header `Link` della home e prosegue su tre
risorse che non entrano nella sitemap e rispondono con `X-Robots-Tag: noindex`:

- `/.well-known/api-catalog`, catalogo RFC 9727 delle interfacce pubbliche;
- `/openapi.json`, contratto OpenAPI dei soli endpoint di lettura documentati;
- `/.well-known/agent-skills/index.json`, indice della skill pubblica
  `query-divario-italia`, con digest SHA-256 verificabile.

La skill descrive come interrogare e interpretare i dati. Non concede nuove
capacità: restano esclusi endpoint di scrittura, giochi, classifiche utenti e
strumenti interni della pipeline.

## Definizione

| priorità | domanda reale | pubblico | URL canonica che deve rispondere | fonte | granularità | anno richiesto | formato ideale | lacune attuali |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | Che cos'è l'indice di vecchiaia e come si legge? | cittadino, studente, giornalista | `/indicatore/indice-di-vecchiaia/ter-921` | Istat, Indicatori demografici | regione | 2026 per l'esempio, definizione indipendente dall'anno | definizione breve, unità, esempio numerico e limite | La definizione primaria può non esplicitare in campi separati numeratore e denominatore. Non vanno dedotti. |
| P1 | Che cosa misura la soddisfazione per la propria vita? | cittadino, comunicatore, ricercatore | `/indicatore/soddisfazione-per-la-propria-vita/bes-08BSO001` | Istat, BES nazionale | regione | 2025 | frase in linguaggio comune, popolazione di riferimento, scala e cautela interpretativa | Il catalogo conserva spesso il perimetro nella definizione testuale, non in metadati strutturati. |

## Dato puntuale

| priorità | domanda reale | pubblico | URL canonica che deve rispondere | fonte | granularità | anno richiesto | formato ideale | lacune attuali |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | Qual è l'età media della popolazione in Lombardia nel 2026? | cittadino, giornalista locale | `/indicatore/eta-media-della-popolazione/ter-920` | Istat, Indicatori demografici | regione, Lombardia | 2026 | una cifra con unità, territorio, anno e link alla fonte | La scheda apre sul primo territorio in classifica. Il selettore consente la Lombardia, ma l'URL non conserva ancora il territorio a fuoco. |
| P1 | Quante famiglie lamentano irregolarità nella distribuzione dell'acqua in Sicilia? | cittadino, amministratore locale | `/indicatore/irregolarita-nella-distribuzione-dell-acqua/ter-6` | Istat, Banca dati territoriale per le politiche di sviluppo | regione, Sicilia | 2025 | valore percentuale, formulazione "ogni 100", anno e caveat campionario | La query chiede "quante", mentre la serie è una quota. Senza numerosità di base non si deve produrre un conteggio assoluto. |

## Classifica

| priorità | domanda reale | pubblico | URL canonica che deve rispondere | fonte | granularità | anno richiesto | formato ideale | lacune attuali |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | Quali regioni hanno l'età media più alta nel 2026? | giornalista, analista, cittadino | `/indicatore/eta-media-della-popolazione/ter-920` | Istat, Indicatori demografici | tutte le regioni | 2026 | tabella ordinata con posizione, valore, unità e parità stabili | Il download non include una colonna di posizione. La classifica resta comunque riproducibile dai valori. |
| P1 | Dove è più alta l'insoddisfazione per l'erogazione del gas? | consumatore, giornalista locale | `/indicatore/grado-di-insoddisfazione-dell-utenza-per-lerogazione-di-gas/ter-231` | Istat, Banca dati territoriale per le politiche di sviluppo | tutte le regioni | 2025 | classifica dal valore più alto, specificando che "più alto" non significa "migliore" | Nessuna lacuna bloccante. Va mantenuta distinta la graduatoria descrittiva da una valutazione di qualità complessiva. |

## Confronto

| priorità | domanda reale | pubblico | URL canonica che deve rispondere | fonte | granularità | anno richiesto | formato ideale | lacune attuali |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | Il valore della Sicilia è più alto di quello della Lombardia per le interruzioni dell'acqua? | cittadino, giornalista | `/indicatore/irregolarita-nella-distribuzione-dell-acqua/ter-6` | Istat, Banca dati territoriale per le politiche di sviluppo | due regioni | 2025 | due valori omogenei, differenza in punti percentuali e collegamento a `/confronto` | La scheda mette a fuoco un territorio alla volta. Il confronto affiancato vive su `/confronto` e lo stato scelto non ha una URL canonica condivisibile. |
| P2 | Quanto è cambiata la soddisfazione ambientale rispetto all'anno precedente? | giornalista, policy maker | `/indicatore/soddisfazione-per-la-situazione-ambientale/bes-10AMB009` | Istat, BES nazionale | regioni presenti in entrambi gli anni | dal 2024 al 2025 | media semplice, base comune, aumenti e diminuzioni, variazione in punti percentuali | Nessuna lacuna bloccante. La risposta deve dire entrambi gli anni se la serie ha un salto temporale. |

## Andamento

| priorità | domanda reale | pubblico | URL canonica che deve rispondere | fonte | granularità | anno richiesto | formato ideale | lacune attuali |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | Come è cambiato l'indice di vecchiaia negli ultimi anni? | studente, demografo, giornalista | `/indicatore/indice-di-vecchiaia/ter-921` | Istat, Indicatori demografici | regione selezionata e media semplice delle regioni | fino al 2026 | serie storica, primo e ultimo anno reale, variazione assoluta con unità | L'immagine iniziale mostra la media e un territorio selezionabile, ma la selezione non è persistita nell'URL. |
| P2 | L'irregolarità dell'acqua sta aumentando o diminuendo? | cittadino, amministratore | `/indicatore/irregolarita-nella-distribuzione-dell-acqua/ter-6` | Istat, Banca dati territoriale per le politiche di sviluppo | regioni su base confrontabile | fino al 2025 | ultimo passaggio separato dal trend lungo, senza attribuire cause | La frequenza di aggiornamento può avere salti. "Annuale" è scorretto quando gli anni non sono consecutivi. |

## Metodologia

| priorità | domanda reale | pubblico | URL canonica che deve rispondere | fonte | granularità | anno richiesto | formato ideale | lacune attuali |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | La media mostrata è la media italiana? | giornalista, ricercatore, fact checker | `/metodologia` e apparato della scheda canonica | metodologia Divario Italia sui dati primari indicati nella scheda | regioni o province | anno visualizzato | risposta netta: media semplice non ponderata, base territoriale e conseguenza | Nessuna lacuna bloccante. Evitare sempre "media Italia" se manca una ponderazione corretta. |
| P1 | Da dove arrivano i dati e che cosa rielabora Divario Italia? | giornalista, riutilizzatore | apparato della pagina indicatore canonica | URL primaria dichiarata per la serie | livello visualizzato | ultimo anno disponibile | fonte, archivio o dataflow, licenza, calcoli derivati e citazione pronta | Alcune famiglie espongono la pagina istituzionale ma non un permalink alla singola tavola o query SDMX. |

## Download

| priorità | domanda reale | pubblico | URL canonica che deve rispondere | fonte | granularità | anno richiesto | formato ideale | lacune attuali |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | Posso scaricare tutti gli anni dell'indicatore in CSV? | data journalist, ricercatore, sviluppatore | pagina indicatore canonica, link `/download/indicator/<id>.csv` | stessa fonte primaria della scheda | tutte le regioni e tutti gli anni disponibili | intera serie, incluso il 2025 o 2026 quando presente | CSV lungo con id, territorio, anno, valore, unità, fonte e URL fonte | Le serie provinciali BES che non entrano nel catalogo dell'atlante non hanno ancora questo endpoint generico. |
| P1 | Esiste un download JSON con metadati e serie? | sviluppatore, ricercatore | pagina indicatore canonica, link `/download/indicator/<id>.json` | stessa fonte primaria della scheda | tutte le regioni | intera serie | oggetto con `metadata` e `series`, più URL canonica documentata dalla pagina | Il JSON è pensato per macchine e non include una graduatoria precalcolata, che va derivata scegliendo anno e regola di ordinamento. |

## Regole di pubblicazione

1. Una nuova formulazione entra nel cluster esistente e punta alla medesima URL
   canonica. Non si crea una pagina quasi identica per "classifica regioni",
   "graduatoria regioni" e "regioni migliori".
2. Le domande mostrate nelle schede sono costruite dal view model comune con
   anno e livello correnti. Sono collegamenti alle risposte già presenti nel
   cruscotto, nell'articolo e nell'apparato, non copie statiche dei numeri.
3. Un eventuale articolo deve aggiungere contesto editoriale reale, seguire
   `content/STYLE.md`, dichiarare l'indicatore nel frontmatter e collegare il
   percorso canonico della scheda. Non sostituisce la scheda per una variante
   lessicale della query.
4. Una domanda P1 perde priorità se l'aggiornamento rende incompleta la
   copertura o interrompe il collegamento alla fonte primaria. La priorità va
   rivalutata dai metadati, non mantenuta per inerzia nel testo.
