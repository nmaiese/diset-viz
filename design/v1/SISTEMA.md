# Divario Italia 1.0: il sistema di pagina

Questo documento dice come sono fatte le pagine della 1.0: la griglia, la
tipografia, i componenti, l'ordine delle sezioni di ogni pagina chiave e le
regole di contenuto che valgono ovunque. I valori (colori, font, misure) stanno
in `tokens/tokens.json`. L'identita' in vigore sul sito resta
`app/static/css/ds/system.css` finche' la migrazione non passa per PR.

## Da dove nasce

Il sito del settembre 2026 non aveva una regia: tre contenitori diversi (1180,
1360, 760) sotto una testata a 1440, 58 taglie di carattere, dieci ricette di
H1, un'etichetta mono maiuscola da 11px come voce dominante, dieci famiglie di
bottoni e sette implementazioni della mappa. Le schede indicatore portano l'87%
dei clic da Google e l'84% delle impression: il sistema si misura su di loro.

## La direzione: Cronaca

Giornalismo dati sul modello di Reuters Graphics, con l'attenzione di The
Upshot per il testo che accompagna il dato.

- **Fondo bianco, una sola famiglia**: Source Sans 3 variabile (OFL). Titoli,
  prosa, interfaccia, numeri ed etichette dei grafici. Il monospazio resta solo
  per i codici (id di serie, URL da copiare).
- **Un solo accento**, arancio bruciato, per cio' che si clicca e per l'unico
  elemento in evidenza in un grafico. Mai un colore dei dati, mai un giudizio.
- **I dati in blu**, rampa sequenziale a sei passi. Divergente blu e ocra solo
  quando il centro e' il valore Italia. Nessun verde e nessun rosso fuori dal
  simbolo del marchio, cosi' una mappa non richiama mai il nord verde e il sud
  rosso del logo.
- **Regia**: ogni pagina apre con la risposta, il numero e un grafico, non con
  un paragrafo. Allineamento a sinistra sotto il marchio. La struttura la fanno
  l'aria e i filetti, mai una scatola dentro l'altra.
- **Marchio**: il simbolo (Italia verde e rossa con le barre) resta com'e'. Il
  wordmark si compone in Source Sans 3, "Divario" a 700 e "Italia" a 400, sempre
  in inchiostro. Niente accento a meno di 24px dal simbolo.

## Griglia

- **Un contenitore solo** da 1200px, condiviso da testata, briciole, contenuto
  e piede: il simbolo, la prima voce delle briciole, l'H1 e il bordo sinistro di
  mappe e tabelle stanno sulla stessa verticale. Margine di pagina 16px sotto i
  600, 24 fino a 959, 32 da 960.
- **Colonne**: 4 sotto i 600, 8 fino a 959, 12 da 960, gutter 16 e poi 24.
- **Tre larghezze nominate**, che partono sempre dalla prima colonna:
  - **testo**: colonne 1-7 con tetto di 38rem, circa 65-70 caratteri. Prosa,
    lede, frase-risposta, note. L'H1 puo' arrivare alla colonna 9.
  - **largo**: colonne 1-10. Modulo dato, tessere, figure larghe, serie.
  - **pieno**: colonne 1-12. Tabelle lunghe, griglie di schede, podi.
- **Margine**: da 1200px le colonne 9-12 accanto al testo ospitano l'indice di
  pagina sticky, la riga fonte e le azioni Cita e Scarica. Sotto, rientrano nel
  flusso.
- **Breakpoint** 600, 960, 1200. Dentro i componenti si usano container query
  sulla larghezza del componente, non altri breakpoint di pagina.
- **Spazi** a passo 4, usati su nove valori: 4, 8, 12, 16, 24, 32, 48, 64, 96.
  Fra sezioni 64 (48 su telefono) con un filetto, fra blocchi 24 (16).
- **Testata** alta 64px (56 su telefono), sticky solo la barra.

## Tipografia

Una scala di ruoli, nominati per funzione:

| ruolo | desktop | telefono | uso |
| --- | --- | --- | --- |
| display | 56/58 | 36/40 | H1 della home e degli articoli |
| titolo | 44/48 | 30/34 | H1 di schede, territori, classifiche |
| sezione | 28/32 | 23/28 | H2, sempre sotto un filetto |
| sottosezione | 20/26 | 19/24 | H3, titolo-affermazione dei grafici |
| lede | 22/32 | 19/28 | frase-risposta, sommario |
| prosa | 19/30 | 18/28 | articolo della scheda, blog, metodologia |
| interfaccia | 16/24 | 16/24 | controlli, celle, schede |
| piccolo | 14/20 | 14/20 | riga fonte, meta, briciole, didascalie |
| etichetta | 13/18, peso 600 | 13/18 | occhielli, intestazioni di tabella, legende |
| cifra chiave | 64/64, peso 700 | 44/44 | tessere e numero di pagina |

- Le etichette sono in minuscolo con l'iniziale maiuscola: mai tutto maiuscolo,
  mai monospazio. 13px e' il minimo, perche' Source Sans ha l'occhio medio
  piccolo.
- Cifre tabellari in ogni colonna. **La riga in evidenza non va mai in
  grassetto**: a peso 700 le cifre sono piu' larghe e rompono l'incolonnamento.
  L'evidenza la fanno il fondo e una barretta di 3px.
- Corsivo vero, caricato solo dove serve.

## Componenti

Venticinque, e ognuno prende il posto delle sue varianti di oggi.

- **Testata**: salto al contenuto, simbolo e wordmark, navigazione (Territori,
  Temi, Qualita' della vita, Atlante e dati con Metodologia, Storie, Quiz),
  ricerca, tema, accesso discreto. Sotto i 960 un cassetto, e nient'altro: niente
  barra in basso.
- **Piede**: una frase di fiducia (istituzioni da `app/sources.py`, licenza,
  metodologia, correzioni, come citare), la mappa del sito in quattro colonne,
  la riga legale. Uno solo, anche sull'atlante.
- **Briciole**: dalla macro `_breadcrumb.html`, uguali al BreadcrumbList.
- **Testata di pagina con risposta**: occhiello-link (tema, istituzione,
  copertura, anno dei dati), H1, frase-risposta, riga meta (fonte, "aggiornato
  il", segnala un errore, preferiti fuori dall'H1).
- **Frase-risposta**: una o due frasi con estremi, territori linkati, anno e
  unita'. E' il frammento che una persona o un assistente cita senza scorrere.
- **Tessere numero**: 3-4 cifre di contesto che la frase non dice, in un `<dl>`,
  separate da filetti verticali, senza scatola.
- **Modulo dato**: una `<figure>` con titolo-affermazione, sottotitolo (misura,
  unita', anno), barra strumenti (livello come link reali, anno, trova il tuo
  territorio), mappa e classifica affiancate da 720px di modulo, riga fonte.
- **Mappa coropletica**: sei gradini da poco a molto contrasto seguendo la
  grandezza, qualunque sia il verso, legenda con tutti e sei. Dato mancante
  tratteggiato, "n.d.". Selezione con contorno in inchiostro, mai in accento.
- **Serie storica**: altezza fissa, etichette dirette a fine linea, media
  semplice tratteggiata, tabella equivalente.
- **Tabella dati**: `caption`, `th scope`, numeri a destra con decimali uniformi,
  solo filetti orizzontali. Sotto i 560px di contenitore le righe diventano
  blocchi etichettati.
- **Classifica a barre**: e' una tabella. Tutte le barre nel grigio di contesto,
  solo la riga scelta in accento. Per 107 province: prime 10 e ultime 10, le
  altre nello stesso DOM dentro un `details`.
- **Barra di posizione e punteggio**: un segno in linea, sempre accanto al
  numero (punteggio 0-100 con tacca a 50, traccia da 1 a N).
- **Segno di verso e movimento**: freccia, segno e parole ("da 12ª a 8ª",
  "meglio se alto"), in colore di testo.
- **Riga fonte**: "Fonte: Istat, Conti economici territoriali (2024).
  Elaborazione Divario Italia." piu' il link ai dati.
- **Nota metodo**: "Come leggere il dato" in due colonne, "In parole semplici"
  e "Secondo la fonte".
- **Cita e riusa**: dato piu' recente, serie, download CSV e JSON, licenza,
  citazione copiabile, versione testo, data di aggiornamento visibile.
- **Continua da qui**: tre corsie, ogni destinazione una volta.
- **Scheda**: una sola card per indicatore, storia, territorio, tema. Il titolo
  e' il link, esteso a tutta la scheda. Niente ombra, niente "Apri".
- **Controlli segmentati**: link quando cambia il documento, bottoni con
  `aria-pressed` quando cambia uno stato. Attivo = fondo pieno.
- **Ricerca**: una per pagina, suggerimenti raggruppati per tipo.
- **Indice di pagina**: domande brevi ("Chi e' in testa", "Com'e' cambiato"),
  sticky nel margine da 1200.
- **Figura dell'articolo**: titolo-tesi in HTML, grafico con testo a taglia
  reale, riga fonte, tabella dei valori.
- **Azione**: un primario al massimo per schermata, secondario a contorno, link
  d'azione con freccia. Niente pillole.
- **Etichetta di stato**: testo piccolo con icona facoltativa, senza pillola
  colorata ("Serie ferma al 2015", "Citta' metropolitana", "n.d.").
- **Slot pubblicitario**: vedi sotto.

## Pagine

### Scheda indicatore

1. Briciole, voce attiva Temi.
2. Testata-risposta, larghezza testo.
3. La risposta in cifre: tessere senza ripetere la lede (in testa o media
   semplice, rapporto fra prima e ultima, variazione, copertura), verso a parole.
4. Indice di pagina nel margine.
5. Confronta i territori: modulo dato, largo.
6. Com'e' cambiato: serie storica con tabella, largo.
7. L'analisi: la prosa scritta con le sue figure, larghezza testo.
8. Come leggere il dato: nota metodo, largo.
9. Fonti, dati e citazione: cita e riusa.
10. Continua da qui, pieno.

Stati da reggere: scheda senza prosa (251 su 634), due livelli regione e
provincia, solo provinciale senza mappa (107 righe), territorio scelto (noindex),
serie di un anno solo, indicatore senza verso, scheda non indicizzabile.

### Home

Testata-risposta con un H1 descrittivo e la ricerca "trova il tuo territorio",
il dato in evidenza (frase calcolata, mappa, classifica dallo zero), regioni per
ripartizione e province, qualita' della vita (doppio podio), il quiz (modulo con
i tre giochi), i temi, le storie, fonti metodo e come citare.

### Regione

Testata-risposta con il localizzatore nel margine, numeri chiave, i temi dal
migliore al peggiore, dove stacca e dove resta indietro con i valori veri, che
cosa e' cambiato, le province della regione, tutti gli indicatori per
macro-area, regioni simili, fonti e citazione.

### Provincia

H1 che e' gia' la risposta ("Lecce e' 79ª su 107 province"), numeri chiave che
non ripetono l'H1, le dimensioni con la linea della media 50, una sola sintesi
forte e debole, che cosa e' cambiato, tutti gli indicatori in colonne pulite
(valore con unita' e anno, variazione, posizione in Italia, posizione nella
regione), le vicine e le sorelle, fonti.

### Articolo

Briciole Home / Storie / tema / titolo, titolo con sommario visibile, firma e
data, la risposta in breve, la copertina, il corpo a misura di lettura con
figure e tabelle, il rimando alla scheda dopo la prima figura, dati e metodo in
un blocco solo, continua a esplorare.

### Classifica della qualita' della vita

H1 con il profilo, frase-risposta (prima, ultima, distanza, anni dei dati),
controlli di livello e profilo come link reali, classifica con barra del
punteggio e tacca a 50, mappa accanto (non sticky), dove eccelle ogni
territorio, metodo fonti e download. L'indice `/qualita-della-vita` usa gli
stessi pezzi con il doppio podio regioni e province.

## Regole di contenuto

- **Numeri** in formato italiano, spazio insecabile fra cifra e unita', unita'
  su ogni cifra isolata e nell'intestazione di colonna.
- **Decimali** da una funzione sola (`seo_titles.format_number`): euro sopra
  1.000 interi, percentuali e indici con un decimale.
- **Date** "17 luglio 2026" in `<time datetime>`. L'anno del dato resta distinto
  dalla data di aggiornamento.
- **Una cifra una volta**: frase-risposta, tessere e titoli dei grafici non si
  ripetono.
- **Media**: "media semplice delle 20 regioni", mai "media nazionale".
- **Colore e giudizio**: nessun colore dice meglio o peggio. Il verso si dice a
  parole.
- **Posizioni** sempre con denominatore e criterio.
- **Titoli dei grafici** come affermazioni verificate, al massimo circa 90
  caratteri.
- **Ogni cifra chiave esiste come testo HTML**, anche nel gemello Markdown.
- **Punteggiatura**: nel testo visibile niente trattino lungo, trattino medio,
  punto e virgola, puntini di sospensione.

## Pubblicita'

Al massimo due spazi per pagina, con altezza riservata per non spostare il
contenuto ed etichetta "Pubblicita'". Mai dentro la testata-risposta, le
tessere, il modulo dato o una tabella. Posizioni: nella scheda dopo "Com'e'
cambiato" e nel margine sotto l'indice da 1200px, in home fra i temi e le
storie, sulle pagine territorio prima di "Tutti gli indicatori", nell'articolo
dopo la prima figura e in coda, nella classifica dopo la tabella. Gli annunci
automatici di AdSense vanno spenti dalla console, altrimenti Google ne aggiunge
dove vuole.

## Accessibilita'

WCAG 2.2 AA come minimo: testo a 4,5:1, controlli e grafici a 3:1, un solo
`<main id="contenuto">` per pagina, focus visibile e uguale dappertutto, mappe
mai con figli focalizzabili dentro `role="img"`, una tabella accanto a ogni
mappa e grafico, bersagli di 44px su telefono, niente scorrimento orizzontale a
320px, `prefers-reduced-motion` rispettato. Il tema scuro ridefinisce ogni
colore per tenere lo stesso contrasto del chiaro, e la rampa va da poco a molto
contrasto col fondo.
