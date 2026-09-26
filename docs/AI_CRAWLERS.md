# Crawler AI e `robots.txt`

Come il sito si presenta ai motori che leggono per rispondere e per addestrare, e
che cosa è ancora da decidere. La regola che il codice applica è in
`app/views.py`, costanti `_ROBOTS_AI_ANSWER_BOTS` e `_ROBOTS_AI_TRAINING_BOTS` e il
segnale di contenuto `_ROBOTS_CONTENT_SIGNAL`. Qui c'è il perché, e la domanda che
`STATUS.md` lascia aperta.

## La regola attuale

Il segnale di contenuto dichiarato è `search=yes,ai-input=yes,ai-train=no`: la
ricerca e la citazione in tempo reale sono permesse, l'addestramento è riservato.
La separazione è possibile per bot che ne fanno due usi distinti, perché OpenAI,
Anthropic e Perplexity hanno user agent diversi per il recupero e per l'addestramento,
e quindi `GPTBot` e `ClaudeBot` restano bloccati mentre `OAI-SearchBot`,
`ChatGPT-User`, `PerplexityBot`, `Perplexity-User`, `Claude-SearchBot` e
`Claude-User` passano.

**Google non ha fatto la stessa scelta.** `Google-Extended` è un token unico che
copre insieme le due cose. Dalla documentazione ufficiale:

> Google-Extended is a standalone product token that web publishers can use to manage
> whether content Google crawls from their sites may be used for training future
> generations of Gemini models that power Gemini Apps and Vertex AI API for Gemini
> and for grounding (providing content from the Google Search index to the model at
> prompt time to improve factuality and relevancy) in Gemini Apps and Grounding with
> Google Search on Vertex AI.
>
> Google-Extended does not impact a site's inclusion in Google Search nor is it used
> as a ranking signal in Google Search.

Fonte: [Google, list of Google's common crawlers](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers),
pagina aggiornata il 14 luglio 2026.

## Perché la domanda di `STATUS.md` ha una risposta che non presuppone

Il follow-up chiede se bloccare `Google-Extended` per rendere la regola di
`robots.txt` coerente con `ai-train=no`. **Non lo renderebbe coerente: lo
contraddirrebbe.** Lo stesso token governa il grounding, che è esattamente
`ai-input`, e il sito oggi lo concede. Bloccarlo farebbe due cose insieme: tiene
lontano Gemini dall'addestramento, che è il fine, e toglie il sito dalle risposte
grounded di Gemini Apps e di Grounding with Google Search, che non è il fine e
contraddice `ai-input=yes`.

Il costo SEO è zero in entrambi i casi, e la stessa fonte lo dice: `Google-Extended`
non influisce sull'inclusione in Google Search e non è un segnale di ranking. Quello
che si perde è la citazione nelle risposte generate, che è il canale che
`docs/LLM_QUERY_MAP.md` lavora per coprire.

## I token che governano l'addestramento, se è quello il punto

Se l'obiettivo è onorare `ai-train=no` nei confronti con Google, il token da
guardare non è `Google-Extended`. Nella stessa pagina ufficiale i crawler generici
di Google sono altri, e oggi **non** compaiono né fra i bot bloccati né fra quelli
autorizzati, quindi li prende la regola `User-agent: *` con `Allow: /`:

| Token | A cosa serve, secondo Google | Situazione attuale |
|---|---|---|
| `GoogleOther` | crawler generico, usato dai team di prodotto, per esempio ricerche interne | non bloccato |
| `GoogleOther-Image` | idem, per le immagini | non bloccato |
| `GoogleOther-Video` | idem, per i video | non bloccato |
| `Google-CloudVertexBot` | scansioni richieste dal proprietario del sito per Vertex AI Agents | non bloccato |

Bloccarli è la scelta coerente con `ai-train=no`, se è quella la priorità, e non
tocca il grounding. Il costo è che non si può più sapere quale uso fa Google di un
token che, per sua stessa ammissione, non è separabile: `GoogleOther` non distingue
una ricerca interna da un addestramento.

Che bloccare questi token non tocchi la ricerca è deduzione, non una frase della
fonte: vale perché `GoogleOther` è un token diverso da `Googlebot`, e bloccare il
primo non blocca il secondo. Per `Google-Extended` invece lo dice esplicitamente la
fonte, e lo riportiamo sopra.

## Cosa resta da decidere, e da chi

La decisione non è tecnica, è di merito, e non è stata presa qui.

- **Tenere tutto com'è**: `Google-Extended` passa, la visibilità nelle risposte
  generate resta aperta, l'addestramento su Gemini resta possibile e non lo
  controlliamo. È la scelta di oggi.
- **Bloccare `Google-Extended`**: si ottiene l'addestramento negato, e in cambio si
  perde il grounding. Coerente con `ai-train=no` solo se si accetta di rinunciare
  anche ad `ai-input=yes`, e allora il segnale di contenuto va cambiato insieme.
- **Bloccare i crawler generici**: più coerente con il segnale, meno deciso, perché
  il token non è separabile per progetto.

Se si sceglie una delle due, il cambiamento è una riga in `app/views.py` e un
test che guardi `robots.txt`, quindi passa da PR con il resto del codice.
