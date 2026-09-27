# Cronaca 2.0: master design blueprint

> Stato: specifica pronta per implementazione
> Data: 27 settembre 2026
> Ambito: home, navigazione, scheda indicatore, pagine territorio e tema
> Baseline: Design System 1.0 "Cronaca" al commit `e07e76b5`

Cronaca 2.0 non sostituisce l'identita' del sito. La rende piu' netta. La
pagina resta editoriale, leggibile e verificabile. Il salto visivo arriva da
scala, ritmo, composizione e risposta dell'interfaccia, non da una seconda
palette o da effetti decorativi.

## Decisioni in una pagina

| Tema | Decisione | Conseguenza |
| --- | --- | --- |
| Direzione cromatica | Palette B, "Data-Visual Dynamic Wow", tradotta dentro i vincoli di Cronaca | Restano inchiostro, arancio per l'interazione e blu per i dati. L'impatto arriva da campiture, scala e composizione |
| Navigazione | Testata sticky compatta e cassetto mobile | Nessuna barra mobile in basso. Le pagine lunghe mantengono piu' spazio e una sola navigazione globale |
| Hero home | Risposta, ricerca e mappa dati affiancate | La persona puo' cercare, capire il prodotto o aprire un territorio senza scorrere |
| Scheda indicatore | Racconto verticale con indice sticky | Niente dashboard a widget. Il bento resta un pattern di sintesi, non sostituisce la sequenza editoriale |
| Griglia bento | Mosaico editoriale asimmetrico su home e pagine indice | Una tessera dominante, poche tessere secondarie e ordine DOM uguale all'ordine di lettura |
| Movimento | Microinterazioni brevi e transizioni che spiegano continuita' | Niente parallax, contatori automatici o animazioni decorative allo scroll |
| Tema scuro | Parita' funzionale col chiaro | Ogni nuovo colore nasce nei token e ha la sua coppia scura |

## Input e limite dell'analisi

Questa specifica usa:

- il sistema esistente in `design/v1/SISTEMA.md`
- i token canonici in `design/v1/tokens/tokens.json`
- i template e i fogli runtime sotto `app/templates/v1/` e
  `app/static/css/ds/`
- la scelta esplicita della Palette B
- una ricerca sulle pratiche e sui segnali di tendenza disponibili al 27
  settembre 2026

Il report disponibile e' `../ux-audit-visuale-2/reports/visual_audit_report.json`,
prodotto dal worktree di audit il 27 settembre 2026. La sintesi dichiara venti
pagine e tre viewport, e conferma la griglia desktop, la gerarchia tipografica e
l'assenza di overflow a 1440, 768 e 375 px. Il report non e' ancora un via
libera completo: nel JSON `/indicatore/tasso-di-occupazione-totale/ter-13/province`
risulta "Pagina non trovata"; per la home `hasResponseSentence` e' falso
nonostante la sintesi dica che la frase-risposta e' presente; il campione
segnala inoltre molti bersagli sotto 44 px, fra cui link e marchio. La
dichiarazione di conformita' dei touch target va ricontrollata distinguendo
controlli, link testuali ed elementi decorativi. I metadati menzionano 320 px,
ma i viewport effettivamente registrati sono 375, 768 e 1440.

Il blueprint usa i risultati coerenti come baseline e tratta le discrepanze come verifiche aperte, non come difetti di design gia' confermati. La riga della rotta non valida viene esclusa; la frase-risposta assente diventa requisito della nuova hero; i touch target vengono ricontrollati distinguendo controlli, link testuali e mappe; il viewport 320 px e' incluso nella matrice anche se manca dal report. Questi punti si chiudono nella verifica della fase di implementazione con URL validi e risultati registrati. Se un rilievo confermato smentisce una misura, si aggiorna prima la specifica e poi il CSS.

## Che cosa significa "wow" per Divario Italia

Il sito non e' un prodotto promozionale e non e' un pannello operativo. E' un
atlante pubblico. L'effetto deve essere una comprensione piu' rapida, non una
decorazione piu' vistosa.

Il principio visivo e' **tensione editoriale**:

1. una risposta grande e concreta
2. una figura dati dominante
3. dettagli piccoli, precisi e quieti
4. molto spazio fra sezioni, poco spazio fra elementi che appartengono alla
   stessa risposta
5. un solo punto arancio che indica dove agire

La Palette B viene quindi applicata cosi':

- superfici alternate gia' presenti, usate per separare i capitoli
- rampa blu resa protagonista in mappe, strisce e numeri
- figure e cifre piu' grandi, con Sofia Sans Semi Condensed
- mosaici asimmetrici solo dove aiutano a scegliere un percorso
- stati di hover e focus netti
- movimento breve quando mostra una relazione fra prima e dopo

Non appartengono a Cronaca 2.0:

- glassmorphism, sfocature e trasparenze su contenuto o controlli
- gradienti puramente decorativi
- ombre su ogni scheda
- angoli molto arrotondati e pillole come linguaggio dominante
- colore arancio usato come serie dati
- mappe, grafici o numeri animati soltanto per attirare attenzione
- 3D, WebGL, video in autoplay o sfondi in movimento

## Evidenza esterna usata

I segnali 2026 convergono su interfacce meno levigate e piu' riconoscibili. Il
rapporto di Canva chiama questa direzione "Imperfect by Design" e lega il
valore alla traccia umana, non all'aggiunta indiscriminata di effetti. Per
Divario Italia significa mostrare la struttura editoriale, i filetti e la
materia del dato, invece di nasconderli dentro card lucide.

Il bento e' un pattern diffuso, ma qui viene trattato come gerarchia. Una
tessera occupa piu' spazio perche' contiene la risposta principale, non per
creare movimento casuale. Sulle pagine narrative, il pattern non si usa.

Per i prodotti dati la domanda viene prima del grafico. La sintesi pubblicata
da Smashing Magazine il 26 agosto 2026 insiste sul passaggio da collezione di
grafici a sequenza di insight. Questo coincide col contratto gia' adottato da
Cronaca, che apre con risposta e figura.

Sul piano tecnico, container query e subgrid sono ormai ampiamente disponibili
e permettono ai moduli di rispondere allo spazio reale. Le View Transition sono
una progressive enhancement, ancora recente rispetto alle altre due. Non
devono quindi diventare un requisito per leggere o usare la pagina.

Fonti:

- [Canva, Design Trends 2026](https://www.canva.com/newsroom/news/design-trends-2026/)
- [Smashing Magazine, Rethinking Data Visualisation](https://www.smashingmagazine.com/2026/08/rethinking-data-visualisation-ux-approach-dashboards/)
- [MDN, container queries](https://developer.mozilla.org/en-US/blog/getting-started-with-css-container-queries/)
- [MDN, subgrid](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Grid_layout/Subgrid)
- [MDN, ViewTransition](https://developer.mozilla.org/en-US/docs/Web/API/ViewTransition)
- [web.dev, prefers-reduced-motion](https://web.dev/articles/prefers-reduced-motion)

## Invarianti del sistema 1.0

Queste regole non sono oggetto di reinterpretazione:

- un contenitore massimo di 1440 px
- 4 colonne su telefono, 8 su tablet, 12 su desktop
- misura della prosa a 38 rem
- Sofia Sans per testo e interfaccia
- Sofia Sans Semi Condensed per titoli e cifre
- `--accent` solo per interazione ed evidenza singola
- `--seq-1` fino a `--seq-6` per la grandezza dei dati
- colori di Nord, Centro e Mezzogiorno stabili in ogni grafico
- significato mai affidato al solo colore
- filetti e spazio prima delle scatole
- HTML server-rendered completo prima di ogni enhancement JavaScript
- tabella o testo equivalente per ogni visualizzazione
- nessun colore cotto fuori da `system.css`

## Contratto dei token

La palette resta invariata. E' gia' verificata per contrasto e daltonismo e
separa marca, interazione e dati. Cambiarla per inseguire un trend produrrebbe
una seconda grammatica.

### Colori e superfici

| Ruolo | Token | Uso |
| --- | --- | --- |
| Pagina | `--bg` | Fondo primario |
| Capitolo | `--surface-1` | Fasce alternate e moduli di contesto |
| Profondita' | `--surface-2` | Stato selezionato quieto, intestazioni e tracce |
| Interazione | `--accent`, `--accent-strong`, `--accent-wash` | Link, azione primaria, focus ed evidenza singola |
| Dati | `--seq-1` fino a `--seq-6` | Valori ordinati dal minore al maggiore |
| Confronto | `--cmp`, `--cat-*`, `--area-*` | Serie di contesto, categorie e ripartizioni |
| Regole | `--rule`, `--rule-strong` | Struttura del layout |

Una superficie dati non riceve un nuovo colore. Usa `--surface-1` come fondo e
la rampa dentro il grafico. Una superficie in evidenza usa `--accent-wash`,
mai un arancio pieno esteso dietro un grafico.

### Tipografia e movimento

I valori seguenti sono il delta proposto per Cronaca 2.0. Gli altri token
restano uguali alla 1.0.

```css
:root {
  --fs-display: clamp(40px, 29.091px + 2.9091vw, 64px);
  --fs-section: clamp(26px, 21.455px + 1.2121vw, 36px);
  --fs-figure: clamp(48px, 37.091px + 2.9091vw, 72px);

  --radius-panel: 6px;
  --motion-fast: 120ms;
  --motion-base: 180ms;
  --motion-slow: 320ms;
  --motion-distance: 8px;
}
```

Regole di adozione:

- i valori si aggiungono prima in `design/v1/tokens/tokens.json`
- `design/v1/tools/tokens.py` deve generare il foglio del prototipo
- gli stessi valori arrivano in `app/static/css/ds/system.css` nella stessa
  modifica runtime
- `--radius-panel` vale solo per grandi moduli interattivi. Schede editoriali,
  tabelle e fasce restano senza raggio o a 4 px
- `--motion-slow` vale per ricomposizioni di dati. Hover e focus usano i token
  piu' rapidi

### Elevazione

Le schede bento non hanno ombra. Il bordo e la differenza di superficie bastano.
L'ombra resta riservata a elementi davvero sovrapposti:

- menu
- popover
- suggerimenti della ricerca
- dialoghi

Questo mantiene la direzione editoriale e riduce il rumore quando molte tessere
sono visibili insieme.

## Griglia responsiva

| Larghezza di riferimento | Colonne | Margine | Gutter | Comportamento |
| --- | ---: | ---: | ---: | --- |
| 375 px | 4 | 16 px | 16 px | Una colonna visiva, ordine DOM lineare |
| 768 px | 8 | 24 px | 16 px | Coppie 4 + 4 o figura a 5 + testo a 3 |
| 1440 px | 12 | 32 px | 24 px | Hero 5 + 7, testo 7, moduli larghi 10, pieno 12 |

I breakpoint restano 600, 960 e 1200 px. Dentro un modulo si usano container
query. `subgrid` puo' allineare titoli, cifre e azioni delle tessere, con una
disposizione leggibile anche senza supporto.

### Bento editoriale

Il mosaico usa la griglia esistente. Non introduce un secondo sistema.

Regole:

1. massimo cinque tessere in un gruppo
2. una sola tessera dominante
3. lo span nasce dalla priorita' del contenuto
4. nessuna altezza basata sulla viewport
5. nessuna tessera dentro un'altra tessera
6. il link principale copre la tessera, senza link annidati
7. l'ordine visivo non diverge dall'ordine DOM
8. ogni tessera regge testo piu' lungo del 30 per cento senza tagli
9. sotto 600 px tutte le tessere diventano blocchi nell'ordine DOM

Composizione desktop consigliata per un gruppo da quattro:

```text
colonne  1  2  3  4  5  6 | 7  8  9 | 10 11 12
riga 1  [ risposta grande   ] [dato 1] [dato 2 ]
riga 2  [ risposta grande   ] [prossimo passo      ]
```

Su tablet la tessera dominante occupa 8 colonne. Le altre diventano due per
riga. Su telefono l'ordine e': risposta, dato 1, dato 2, prossimo passo.

### Dove usare il bento

- porte principali della home
- apertura di una pagina regione o provincia, per numeri e prossimi passi
- selezione dei temi
- riepilogo di una classifica

Non usarlo in:

- corpo di un articolo
- analisi della scheda indicatore
- tabelle e classifiche lunghe
- metodo, fonti e citazione
- moduli con una sequenza temporale da leggere in ordine

## Navigazione

### Desktop, da 960 px

- barra sticky alta 64 px
- marchio a sinistra
- voci globali sempre visibili al centro
- ricerca, tema e account a destra
- stato attivo indicato da testo e filetto, non dal solo colore
- menu a tendina con massimo due livelli e nessun mega menu promozionale
- ogni tendina usa il pattern disclosure: pulsante con `aria-expanded` e
  `aria-controls`, Enter o Spazio apre e chiude, Escape chiude e restituisce il
  focus al pulsante; Tab segue l'ordine naturale dei link senza intrappolare il
  focus. Non si usano i ruoli ARIA `menu` e `menuitem`
- se una voce ha sia una destinazione sia una tendina, il link alla destinazione
  e il pulsante di apertura sono controlli distinti

### Tablet e telefono, sotto 960 px

- barra alta 56 px che si ritira scorrendo verso il basso e riappare scorrendo
  verso l'alto, come nella 1.0; non si ritira nei primi 120 px, con drawer aperto
  o quando il focus e' dentro la testata
- marchio, ricerca, tema e menu
- il menu apre un cassetto a tutta altezza utile
- le destinazioni seguono la stessa tassonomia del desktop
- il focus entra nel cassetto, resta nel cassetto e torna al comando che lo ha
  aperto
- `Escape`, pulsante chiudi e clic sul fondale chiudono il cassetto
- il corpo non scorre mentre il cassetto e' aperto
- il drawer aperto mantiene la testata visibile e non attiva il ritiro allo scroll

La bottom navigation non viene adottata. Il sito ha piu' di cinque destinazioni
globali, pagine lunghe e gia' due aiuti contestuali fissi, indice e striscia.
Una seconda barra ridurrebbe lo spazio e duplicherebbe il menu.

## Hero della home

### Desktop 1440

```text
┌──────────────── 5 colonne ───────────────┬──────────── 7 colonne ────────────┐
│ occhiello                                │ tesi della mappa                  │
│ H1                                      │ mappa Italia                     │
│ frase risposta                           │ legenda                          │
│ ricerca territorio o indicatore          │ estremi e link classifica         │
│ indicatore in evidenza, forma compatta    │                                  │
└──────────────────────────────────────────┴───────────────────────────────────┘
┌──────────────────────── porte del sito, mosaico editoriale ─────────────────┐
└──────────────────────────────────────────────────────────────────────────────┘
```

La mappa non e' uno sfondo. E' una figura con titolo, legenda, alternativa
testuale e link. La ricerca resta il controllo principale.

### Tablet 768

- titolo e ricerca occupano tutta la larghezza
- sotto titolo e ricerca, mappa e indicatore in evidenza si impilano a tutta
  larghezza, mappa prima
- le porte principali diventano 4 + 4

### Telefono 375

Ordine:

1. occhiello
2. H1
3. risposta
4. ricerca
5. indicatore in evidenza
6. porte principali
7. link alla mappa e alla classifica

La mappa completa non e' necessaria sopra la piega e puo' seguire le porte.
Sotto 600 px puo' essere sostituita dal link alla classifica solo se la pagina
mostra anche una lista testuale delle regioni con gli stessi valori, anno,
legenda e stato del dato della mappa. La ricerca e la porta Regioni da sole non
sono un equivalente: danno accesso ai profili, ma non comunicano i valori.

I numeri sono gia' corretti nell'HTML. Non si usano contatori che partono da
zero, per evitare ritardi, movimento inutile e valori temporaneamente falsi.

## Scheda indicatore

La scheda resta una storia verticale. Il lettore deve poter rispondere in
ordine a cinque domande:

1. che cosa misura
2. chi e' in testa
3. quanto e' grande il divario
4. come e' cambiato
5. come si verifica e si riusa

### Desktop

```text
┌──────────────── testo 1-7 ───────────────┬──── margine 9-12 ────┐
│ briciole, occhiello, H1, risposta         │ tessere numero        │
│ meta e verso                              │                       │
├──────────────────── figura del divario, colonne 1-12 ───────────┤
├──────────────────── prosa 1-7 ───────────┬──── indice 9-12 ─────┤
│                                          │ sticky                │
├──────── figure e moduli nel flusso, colonne 1-12 ────────────────┤
└──────────────────────────────────────────────────────────────────┘
```

Da 1200 px l'indice resta nel margine destro, coerente col sistema 1.0; non
passa a sinistra del contenuto. Le figure che richiedono tutta la larghezza
precedono o seguono il tratto con indice sticky, non gli scorrono sotto.
Durante la prosa, la mappa contestuale non occupa lo stesso margine sticky:
diventa una figura nel flusso prima o dopo il passaggio a cui si riferisce.
Sotto 1200 px l'indice diventa la barra orizzontale gia' prevista.

Le tessere numeriche possono usare la logica bento soltanto nella testata. Il
resto mantiene il ritmo figura, spiegazione, tabella, fonte.

### Tablet e telefono

- H1 e risposta prima di ogni numero accessorio
- tessere in 2 colonne, poi una colonna sotto 420 px
- indice come barra orizzontale sotto la testata
- striscia compatta sotto la barra, entro i limiti gia' definiti per altezza
- mappa e classifica impilate, mappa prima
- tabella trasformata in blocchi etichettati dal suo container, non dal
  viewport
- azioni Cita e Scarica nel flusso

La variante bento completa viene rifiutata per la scheda. Spezzare confronto,
serie, analisi e metodo in widget concorrenti rende meno chiaro il filo e
penalizza lettura, citazione e tastiera.

## Pagine territorio e tema

### Regione e provincia

L'apertura usa un mosaico controllato:

- titolo risposta su 7 colonne
- mappa territoriale su 5 colonne
- tre numeri chiave in una riga comune
- una tessera "Dove stacca" dominante
- una tessera "Dove resta indietro" secondaria

La tabella di tutti gli indicatori resta fuori dal mosaico, a piena larghezza.

### Tema

La striscia del punteggio resta la figura principale. Classifica e mappa sono
un solo modulo dati, non due card indipendenti. Gli indicatori da cui partire
possono diventare un mosaico 6 + 3 + 3 su desktop, 8 + 4 + 4 su tablet e una
colonna su telefono.

## Movimento e feedback

| Evento | Durata | Proprieta' | Regola |
| --- | ---: | --- | --- |
| Hover o pressione | 120 ms | colore, fondo, bordo | Nessun movimento necessario |
| Apertura menu o popover | 180 ms | opacita', translate massimo 8 px | Stato finale subito disponibile |
| Cambio di vista nello stesso modulo | 180 ms | crossfade | Altezza riservata prima del cambio |
| Ricomposizione di punti o tessere | 320 ms | transform, opacita' | Solo se mostra la continuita' dello stesso dato |
| Navigazione fra schede gemelle | 180-320 ms | View Transition | Progressive enhancement |

Con `prefers-reduced-motion: reduce`:

- nessuna traslazione
- nessuna ricomposizione dei punti
- crossfade opzionale e breve
- contenuto finale immediatamente visibile

Lo stato non dipende mai da `animationend`.

## Accessibilita'

Il minimo resta WCAG 2.2 AA. Il progetto mantiene bersagli da 44 px, piu'
grandi dei 24 px richiesti dal criterio 2.5.8. I link dentro una frase restano
l'eccezione prevista dal criterio.

Requisiti:

- testo a 4,5:1 e componenti a 3:1
- focus sempre visibile, almeno 2 px e con contrasto sufficiente
- focus non coperto da testata, barra indice o striscia
- nessuna informazione affidata al solo colore
- ordine della tastiera uguale all'ordine visivo
- nessun `tabindex` positivo
- nessun contenuto essenziale dentro pseudo-elementi
- mappe senza figli focalizzabili dentro `role="img"`
- tabelle equivalenti per ogni grafico
- controlli da 44 px su input coarse
- nessuno scorrimento orizzontale a 320 px
- testo al 200 per cento senza perdita di contenuto o funzione

Riferimenti:

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [W3C, Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)
- [W3C, Focus Appearance](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance)

## Performance e robustezza

Cronaca 2.0 non introduce un framework client.

Budget per pagina:

- nessun nuovo font o peso di font
- nessun video o immagine decorativa nella hero
- CSS nuovo massimo 12 KB gzip per il sistema condiviso
- JavaScript nuovo massimo 6 KB gzip per pagina
- nessun handler che ricalcola layout a ogni evento di scroll
- animazioni solo con `transform` e `opacity`, salvo colore e bordo
- dimensioni riservate per mappe, grafici, immagini e annunci
- contenuto e navigazione completi senza JavaScript

Obiettivi di campo:

- LCP al 75esimo percentile non oltre 2,5 secondi
- INP al 75esimo percentile non oltre 200 ms
- CLS al 75esimo percentile non oltre 0,1

Il dato va verificato in campo. Lighthouse locale serve per trovare regressioni,
non sostituisce GA4, CrUX o un'altra misura reale.

Riferimento: [web.dev, Interaction to Next Paint](https://web.dev/articles/inp).

## Piano di implementazione

### 0. Riconciliare l'audit visuale

- usare le sole rotte valide e registrare pagina e viewport verificati
- verificare frase-risposta home, touch target e viewport 320 px come stabilito
  nella sezione Input e limite dell'analisi
- associare ogni rilievo confermato a pagina, breakpoint, selettore e criterio
  qui sotto
- aggiornare questa specifica se una misura viene smentita

### 1. Token

File:

- `design/v1/tokens/tokens.json`
- `design/v1/src/css/tokens.css`, generato
- `app/static/css/ds/system.css`

Controlli:

```bash
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py design/v1/tools/tokens.py
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py design/v1/tools/check_tokens.py
```

### 2. Navigazione

File:

- `app/static/css/ds/chrome.css`
- macro della testata in `app/templates/`
- `frontend/src/site/` soltanto se il cassetto richiede comportamento nuovo

Il DOM e la tassonomia non cambiano senza una decisione distinta.

### 3. Hero e mosaico home

File:

- `app/templates/v1/home/_top.html`
- `app/static/css/ds/pages/home.css`
- `app/static/css/ds/components.css` per il solo pattern condiviso

La home mantiene dati, copy e URL esistenti. Il refactoring riguarda regia e
gerarchia.

### 4. Scheda indicatore

File:

- `app/templates/v1/indicatore.html`
- `app/static/css/ds/pages/indicatore.css`
- `app/static/css/ds/components.css`

Non si cambia `app/indicator_view.py` se la nuova regia non richiede dati
nuovi. Se serve un dato, va composto nel view model e non calcolato nel
template.

### 5. Territori e temi

Si porta il pattern solo dopo home e scheda. Prima si misura la tenuta del
componente con titoli lunghi, dati mancanti e tema scuro.

## Matrice di accettazione

| Area | 1440 px | 768 px | 375 px | 320 px |
| --- | --- | --- | --- | --- |
| Testata | voci visibili; disclosure apre/chiude, Escape restituisce il focus | cassetto e focus; scroll verso il basso ritira la testata, verso l'alto la mostra | scroll con eccezioni nei primi 120 px, focus nella testata e drawer aperto | nessun overflow |
| Home hero | 5 + 7, mappa leggibile | risposta e ricerca, poi mappa e indicatore impilati in quest'ordine | risposta e ricerca prima; mappa equivalente alla lista testuale | nessun testo tagliato e valori mappa disponibili in testo |
| Bento | span 6 + 3 + 3 | 8, poi 4 + 4 | una colonna | una colonna |
| Indicatore | margine e indice sticky | indice orizzontale | striscia e indice entro 25% altezza | nessun overflow |
| Tabelle | intestazioni e cifre allineate | stack dove previsto | etichette per riga | contenuto completo |
| Tema scuro | token e stati leggibili, screenshot con `prefers-color-scheme: dark` | uguale | uguale | uguale |
| Tastiera | ordine e focus visibili; tendina raggiungibile con Tab e operabile con Enter/Spazio, Escape restituisce il focus | focus confinato nel drawer e ripristinato alla chiusura | nessun controllo irraggiungibile; auto-hide non copre il focus | uguale |
| Motion reduce | niente traslazione o ricomposizione, contenuto finale immediato | uguale | uguale | uguale |

Controlli finali:

```bash
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m unittest discover -s tests/unit -v
DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m unittest discover -s tests -v
node design/v1/tools/shots.mjs giro http://127.0.0.1:5050 /tmp/cronaca-2 /,/indicatore/pil-pro-capite/ter-901,/regione/puglia,/tema/lavoro
THEME=dark node design/v1/tools/shots.mjs giro http://127.0.0.1:5050 /tmp/cronaca-2-dark /,/indicatore/pil-pro-capite/ter-901,/regione/puglia,/tema/lavoro
MOTION=no-preference node design/v1/tools/shots.mjs giro http://127.0.0.1:5050 /tmp/cronaca-2-motion /,/indicatore/pil-pro-capite/ter-901,/regione/puglia,/tema/lavoro
node design/v1/tools/shots.mjs tastiera http://127.0.0.1:5050 /,/regione/puglia
git diff --check
```

`giro` registra nel report la preferenza di movimento: `reduce` per default,
`no-preference` se richiesto. I due giri controllano gli stessi quattro percorsi,
viewport, stati finali e assenza di errori. `tastiera` verifica disclosure
desktop, Escape e ritorno del focus; il giro responsive verifica ritiro e
riapparizione della testata.

## Definition of done

Cronaca 2.0 e' pronta quando:

- l'audit visuale e' collegato a questa matrice
- token canonici, prototipo e runtime non divergono
- home, indicatore, regione e tema sono verificate ai quattro viewport
- chiaro, scuro, tastiera e reduced motion passano nello stesso giro
- nessuna pagina dipende da JavaScript per contenuto, URL o navigazione
- la suite completa e i controlli dei token sono verdi
- il confronto mostra un miglioramento misurabile di gerarchia senza perdita
  di contenuto, accessibilita' o velocita'
