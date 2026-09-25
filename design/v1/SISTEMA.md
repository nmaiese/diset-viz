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

- **Fondo bianco, una famiglia con due larghezze**: Sofia Sans (OFL) per il testo
  e l'interfaccia, Sofia Sans Semi Condensed per i titoli e le cifre. Scelta su
  uno specimen col contenuto vero contro Mona Sans (in colonna lo zero diventa
  barrato), Schibsted Grotesk e Source Serif 4. Il monospazio resta solo per i
  codici.
- **Un solo accento**, arancio bruciato, per la prosa linkata, l'azione
  principale e l'unico elemento in evidenza in un grafico. I link degli elenchi,
  delle schede e delle tabelle sono in inchiostro. Mai un colore dei dati, mai un
  giudizio.
- **I dati in blu**, rampa sequenziale a sei passi. Divergente blu e ocra solo
  quando il centro e' il valore Italia. **Le ripartizioni hanno un colore fisso**,
  uguale in ogni grafico e nei pallini delle classifiche: Nord blu, Centro oliva,
  Mezzogiorno prugna, verificati per i daltonici (`area-*` nei token). Nessun verde e nessun rosso fuori dal
  simbolo del marchio, cosi' una mappa non richiama mai il nord verde e il sud
  rosso del logo.
- **Regia**: ogni pagina apre con la risposta, il numero e un grafico, non con
  un paragrafo. Allineamento a sinistra sotto il marchio. La struttura la fanno
  l'aria e i filetti, mai una scatola dentro l'altra.
- **Marchio**: il simbolo (Italia verde e rossa con le barre) resta com'e'. Il
  wordmark si compone in Sofia Sans, "Divario" a 700 e "Italia" a 400, sempre
  in inchiostro. Niente accento a meno di 24px dal simbolo.

## Griglia

- **Un contenitore solo** da 1440px, condiviso da testata, briciole, contenuto
  e piede, e anche da `.wrap` delle pagine ancora su `site.css`: il simbolo, la
  prima voce delle briciole, l'H1 e il bordo sinistro di mappe e tabelle stanno
  sulla stessa verticale. Margine di pagina 16px sotto i 600, 24 fino a 959, 32
  da 960. Era da 1200: a 1920 pixel lasciava 360 pixel vuoti per lato e metteva
  tutto in una colonna stretta al centro. La misura del testo non cambia,
  crescono mappe, tabelle, griglie e grafici.
- **Colonne**: 4 sotto i 600, 8 fino a 959, 12 da 960, gutter 16 e poi 24.
- **Tre larghezze nominate**, che partono sempre dalla prima colonna:
  - **testo**: colonne 1-7 con tetto di 38rem, circa 65-70 caratteri. Prosa,
    lede, frase-risposta, note. L'H1 puo' arrivare alla colonna 9.
  - **largo**: colonne 1-10. Modulo dato, tessere, figure larghe, serie.
  - **pieno**: colonne 1-12. Tabelle lunghe, griglie di schede, podi.
- **Margine**: da 1200px le colonne 9-12 accanto al testo ospitano l'indice di
  pagina sticky, la riga fonte e le azioni Cita e Scarica. Nella scheda
  indicatore il margine accanto alla testata porta le tessere, una sotto
  l'altra. Sotto i 1200, tutto rientra nel flusso.
- **Breakpoint** 600, 960, 1200. Dentro i componenti si usano container query
  sulla larghezza del componente, non altri breakpoint di pagina.
- **Spazi** a passo 4, usati su nove valori: 4, 8, 12, 16, 24, 32, 48, 64, 96.
  Fra sezioni 64 (48 su telefono) sotto la testata di sezione, fra blocchi 24
  (16).
- **La testata di sezione** e' un filetto d'inchiostro da 3px con l'H2 sotto,
  a 34px da 1200. Col filetto chiaro da 1px e l'H2 poco piu' grande dei titoli
  dei grafici, a schermo largo le sezioni si confondevano una con l'altra.
- **La fascia** (`.zone`) e' una sezione a tutta larghezza col suo contenitore
  dentro. Le pagine che sono un indice di sezioni, la home per prima, alternano
  le fasce fra il fondo e la superficie (`.zone--tint`), cosi' ogni sezione ha
  un inizio e una fine visibili da lontano. La testata della fascia tiene a
  sinistra il titolo con la sua frase e a destra il link alla sezione intera,
  sotto lo stesso filetto.
- **Testata** alta 64px (56 su telefono), sticky solo la barra.

## Tipografia

Una scala di undici ruoli, nominati per funzione:

| ruolo | desktop | telefono | uso |
| --- | --- | --- | --- |
| display | 56/58 | 36/40 | H1 della home e degli articoli |
| titolo | 44/48 | 30/34 | H1 di schede, territori, classifiche |
| sezione | 28/32, 34/39 da 1200 | 23/28 | H2, sempre sotto il filetto d'inchiostro |
| sottosezione | 20/26 | 19/24 | H3, titolo-affermazione dei grafici |
| lede | 22/32 | 19/28 | frase-risposta, sommario |
| prosa | 19/30 | 18/28 | articolo della scheda, blog, metodologia |
| interfaccia | 16/24 | 16/24 | controlli, celle, schede |
| piccolo | 14/20 | 14/20 | riga fonte, meta, briciole, didascalie |
| etichetta | 13/18, peso 600 | 13/18 | occhielli, intestazioni di tabella, legende |
| cifra chiave | 64/64, peso 700 | 44/44 | il numero di una pagina |
| cifra di tessera | 36/38, peso 700 | 28/30 | tessere numero |

- Le etichette sono in minuscolo con l'iniziale maiuscola: mai tutto maiuscolo,
  mai monospazio. 13px e' il minimo. La scala e' tarata su un occhio medio di
  0,49 e `font-size-adjust` la tiene uguale se si cambia famiglia.
- **Le cifre hanno un sistema solo**, `tools/numfmt.py`, per ruoli: cifra (tessere
  e frasi, decimali dalla grandezza), cella (decimali uguali per tutta la
  colonna), punteggio (un decimale), rapporto (un decimale), variazione (sempre
  col segno, "invariato" sullo zero), posizione ("14ª su 20"), conteggio
  (intero). Il segno negativo e' il meno tipografico. Ogni cifra e' un `<data
  value>` col valore per le macchine. L'eccezione e' la cella Andamento
  dell'atlante: tre cifre per riga su 594 righe, e i `<data>` pesavano troppo
  sul tetto di 90 KB compressi, quindi li' la variazione e' testo. L'unita' segue piu' piccola e in
  `--text-2`, la percentuale resta attaccata. I template non formattano mai: usano
  i filtri `num`, `rank`, `delta`.
- Fuori dalle colonne le cifre sono proporzionali (in una tessera le tabellari
  lasciano buchi), in colonna sono tabellari. **La riga in evidenza non va mai in
  grassetto**: a peso 700 le cifre sono piu' larghe e rompono l'incolonnamento.
  L'evidenza la fanno il fondo e una barretta di 3px.
- Corsivo vero, caricato solo dove serve.

## Componenti

Ventotto, e ognuno prende il posto delle sue varianti di oggi.

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
  separate da filetti verticali, senza scatola. Nel margine della scheda, da
  1200, una sotto l'altra con filetti orizzontali.
- **Porte del sito**: in home, sotto la testata, le quattro destinazioni
  grandi (regioni, province, temi, qualita' della vita) con la cifra che le
  misura, calcolata e mai scritta a mano, poi le altre in fila (atlante,
  confronto, divari regionali, storie, quiz, catalogo). I percorsi sono quelli
  di `app/nav.py`: ogni porta e' una voce del menu e ogni tendina ha una porta.
  Il titolo e' il link, esteso a tutta la scheda.
- **Modulo dato**: una `<figure>` con titolo-affermazione, sottotitolo (misura,
  unita', anno), barra strumenti (livello come link reali, anno, trova il tuo
  territorio), mappa e classifica affiancate da 720px di modulo, riga fonte.
  Il livello che manca a una scheda, quando sta in una scheda gemella, e' una
  voce del selettore come le altre e porta all'altra pagina.
  E' un componente: `ui.explore(m, root=...)` in `v1/_ui.html`, che legge un
  solo dizionario, `d.module`, composto da `derive` della pagina con le cifre
  che gia' calcola. Il suo JSON (`data-explore-data`) sta in fondo al modulo.
  Il JavaScript e' `DiV1.init(root)` di `static/js/v1.js`: il caricamento la
  chiama sul documento, e si richiama su un pezzo di pagina nuovo senza
  agganci doppi (il segno sta in una WeakMap). Il confine entro cui il modulo
  cerca i suoi pezzi e' il `data-page-root` piu' vicino. Sulla scheda sta sul
  `<main>`, perche' la striscia in testa e la serie di "Com'e' cambiato" sono
  fuori dal modulo. Da solo (`root=True`) il modulo e' il confine di se stesso.
- **Mappa coropletica**: sei gradini da poco a molto contrasto seguendo la
  grandezza, qualunque sia il verso, legenda con tutti e sei. Dato mancante
  tratteggiato, "n.d.". Selezione con contorno in inchiostro, mai in accento.
  Regioni o province (`ui.map(..., level=)`): sulle province i confini
  regionali si ridisegnano sopra, piu' larghi nel colore del fondo. I contorni
  delle province li scrive `design/v1/tools/province_map.py` (Istat via
  openpolis, CC BY 4.0, attribuzione nella riga fonte) nella stessa proiezione
  delle regioni. Dove le mappe sono piu' d'una i tracciati stanno in uno
  sprite (`v1_map_sprite(livello)`) e la mappa li richiama con `use=True`.
  La scheda la disegna per tutti e due i livelli, e al cambio d'anno un
  territorio senza dato prende il tratteggio (le province con un dato cambiano
  da un anno all'altro).
- **Mappa per scegliere** (`ui.navmap`): non porta un dato, serve a scegliere
  un territorio. Colori dell'interfaccia, mai della rampa: terra nel grigio
  della superficie, confini nel colore del fondo, il territorio scelto o sotto
  il mouse nell'accento, perche' e' un link. Ogni tracciato porta al profilo
  senza JavaScript, fuori dall'ordine di tabulazione e nascosto ai lettori di
  schermo: la tastiera ha il campo o l'indice accanto.
- **Distintivo**: un quadrato di 44 pixel con un'icona, su un lavaggio
  dell'interfaccia (ambra, verde, blu, rosso, o la superficie). Riconosce
  un'area o un impegno a colpo d'occhio. Non e' un colore dei dati e non da'
  un giudizio: testa e coda di una classifica le dicono le frecce.
- **Serie storica**: altezza fissa, etichette dirette a fine linea, media
  semplice tratteggiata, tabella equivalente.
- **Tabella dati**: `caption`, `th scope`, numeri a destra con decimali uniformi,
  solo filetti orizzontali. Sotto i 560px di contenitore le righe diventano
  blocchi etichettati.
- **Classifica a barre**: e' una tabella. Tutte le barre nel grigio di contesto,
  solo la riga scelta in accento. Per 107 province: prime 10 e ultime 10, le
  altre nello stesso DOM dentro un `details`. In home la classifica sta in due colonne da
  dieci per tutti e due i livelli (regioni dalla 1ª alla 10ª e dalla 11ª alla
  20ª, province le prime e le ultime dieci).
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
  `aria-pressed` quando cambia uno stato. Attivo = fondo pieno. Il selettore
  Regioni/Province della home e' un caso di mezzo: senza JavaScript sono due
  link a `?livello=`, con JavaScript diventano schede (tab) con i ruoli ARIA e
  le frecce, e il pannello dell'altro livello e' gia' in pagina. Le linguette
  Regioni/Province della scheda invece cambiano documento: ognuna linka l'URL
  del suo livello, la base o la `/province`, mai un `?livello=`.
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

### I grafici

- **La striscia del divario** e' il segno della 1.0: ogni territorio un punto
  sulla stessa scala, nel colore della sua ripartizione, i due estremi nominati,
  la media semplice, la distanza fra primo e ultimo (in volte, o in punti per i
  punteggi). Apre ogni pagina il cui argomento e' un divario, e sulle pagine di
  un territorio ne evidenzia il punto.
- **La serie a fascia**: la fascia fra il valore piu' alto e il piu' basso di
  ogni anno, la media semplice tratteggiata, i due territori agli estremi nel
  colore della loro ripartizione. La larghezza della fascia e' il divario nel
  tempo.
- **La mappa nomina i suoi estremi** con un richiamo che parte dal baricentro
  del pezzo piu' grande della regione.
- **La sparkline** (`charts.spark`, filtro `sparkline` nei template): una serie
  per anno, mai per posizione, in due taglie a pixel veri (s 88x28, m 120x32),
  linea e punto finale in `--cmp`, mai l'accento e mai la rampa. La scala
  verticale ha un pavimento, lo scarto interquartile dei territori, perche' una
  media che si muove poco non sembri una salita. E' `aria-hidden`: accanto c'e'
  sempre la cifra in testo, con l'anno e di che media e' ("media semplice delle
  regioni con il dato"). Sotto i due punti non si disegna. Nelle tabelle delle
  pagine regione e provincia la sparkline e' quella del territorio, mai una
  media, nella cella `.trend` con "dal 2018 era 64,1": a capo sotto i 1100 px,
  a tutta riga quando la tabella si impila (`.stackwrap--wide`, sotto i 720).
- Ogni grafico esce in due tagli, largo e stretto, perche' il testo resti a
  12-13 pixel veri anche sul telefono, e ha accanto una tabella con gli stessi
  dati. La striscia e la serie a fascia ne hanno un terzo da 1180 pixel, che
  prende il posto del largo da 1100 pixel di grafico: col contenitore a 1440 il
  taglio da 920 lasciava vuoto un terzo della riga. Si disegna lato server in
  `tools/charts.py` (nel sito `app/design/charts.py`), i colori stanno nel CSS.

### Dove stanno oggi

Il foglio comune e' `src/css/components.css`. I componenti nati dentro una
pagina nella prima iterazione hanno ora una versione comune: la classifica col
punteggio (`.table--rank`), la tabella che sotto i 560 pixel diventa blocchi
etichettati (`.table--stack`), la traccia di posizione (`.track`), il
localizzatore (macro `locator`), la barra attorno a 50 (`.divbar`), il podio
(`.podiums`), la figura dell'articolo (`.figure`), l'immagine d'apertura
(`.hero-img`). I fogli in `src/css/pages/` tengono solo l'impaginazione propria
di una pagina.

## Pagine

### Scheda indicatore

1. Briciole, voce attiva Temi.
2. Testata-risposta, larghezza testo.
3. La risposta in cifre: tessere senza ripetere la lede (in testa o media
   semplice, rapporto fra prima e ultima, variazione, copertura), verso a parole.
   Da 1200 nel margine accanto alla testata.
4. Indice di pagina nel margine.
5. Confronta i territori: modulo dato, largo.
6. Com'e' cambiato: serie storica con tabella, largo.
7. L'analisi: la prosa scritta con le sue figure, larghezza testo.
8. Come leggere il dato: nota metodo, largo.
9. Fonti, dati e citazione: cita e riusa.
10. Continua da qui, pieno.

Stati da reggere: scheda senza prosa (251 su 634), due livelli regione e
provincia, solo provinciale (mappa delle province, 107 righe), territorio scelto (noindex),
serie di un anno solo, indicatore senza verso, scheda non indicizzabile.

### Home

Una sequenza di fasce che alternano fondo e superficie, un partial per fascia
in `app/templates/v1/home/`. Testata-risposta con un H1 descrittivo e la
ricerca "trova il tuo territorio", e da 960 pixel la mappa per andare a una
regione, sulla superficie insieme alle porte del sito.

Poi l'indicatore in evidenza, **uno a caso a ogni visita** (`app/home_pick.py`):
una coppia indicatore e livello dal catalogo indicizzabile, prima il livello e
poi l'indicatore, cosi' le province escono una volta su due e non una su otto.
Sta in una scheda con la sua testata, e il nome dell'indicatore e' piu' piccolo
del titolo di sezione. Regioni e province hanno la stessa forma: la striscia
del divario su tutta la larghezza (taglio largo a `HOME_STRIP_WIDTH`), poi la
mappa accanto alla classifica in due colonne. Se l'indicatore sta nel pool a
tutti e due i livelli, il selettore passa dall'uno all'altro senza ricaricare.
`?indicatore=ter-901&livello=provincia` fissa la scelta, se quella coppia sta
nel pool. Per questo la home non sta nella cache di pagina.

Seguono regioni e province (per ognuno dei due livelli la mappa per scegliere,
un territorio a caso e l'anteprima della sua scheda, con le frasi della sua
testata), i temi (le quattro aree col distintivo, testa e coda con le
frecce), la qualita' della vita come porta (che cosa misura, i profili di
priorita', il bottone verso la pagina: la classifica in home non c'e'), il
quiz in una fascia sua (lavaggio ambra, schede con illustrazione, una domanda
lampo), le storie (una grande accanto alla foto, tre in fila) e fonti, metodo
e come citare. Un bottone primario per fascia.

I prototipi in `design/v1/src/` non hanno ancora queste fasce: la home del
sito e' andata avanti da sola.

### Atlante

`/atlante`, dal 25 settembre 2026 resa dal server (`app/design/pages/atlante.py`,
`v1/atlante.html`, `css/ds/pages/atlante.css`). Briciole, testata-risposta con
cifre calcolate, "Sulla mappa" con il modulo dato della scheda su un indicatore
fisso, poi "Tutti gli indicatori": una `.table` per tema con tutte le serie,
link alla scheda, sparkline `m` della media semplice sul pannello fisso,
variazione in chiaro con i due anni, ultimo anno e regioni, "Serie parziale"
come etichetta di stato e "Copertura variabile" al posto della linea quando il
pannello non regge. Il bottone "Sulla mappa" di una riga e' un GET
(`form`, `?mappa=`). Filtri, ricerca e ordine sono un'isola
(`static/js/atlante.js`) sui `data-*` delle righe: senza JavaScript l'elenco
c'e' tutto. I gruppi portano `content-visibility: auto`.

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
data, la copertina larga quanto il contenitore e sopra la piega (con le sue
proporzioni, didascalia e credito), la risposta in breve, il corpo a misura di
lettura con figure e tabelle, il rimando alla scheda dopo la prima figura, dati
e metodo in un blocco solo, continua a esplorare.

### Classifica della qualita' della vita

H1 con il profilo, frase-risposta (prima, ultima, distanza, anni dei dati),
controlli di livello e profilo come link reali, classifica con barra del
punteggio e tacca a 50, mappa accanto (non sticky), dove eccelle ogni
territorio, metodo fonti e download. L'indice `/qualita-della-vita` usa gli
stessi pezzi con il doppio podio regioni e province.

## Regole di contenuto

- **Percentuali**: ogni forma percentuale della fonte ("valori percentuali",
  "percentuale") si scrive "%" (`numfmt.phrase_unit`, e `indicator_notes.
  figure_unit` per chi ha solo nome e unita' della fonte). Variazioni e
  differenze fra tassi restano "punti percentuali", per intero, anche nel
  titolo di "Com'e' cambiato".
- **Numeri** in formato italiano, spazio insecabile fra cifra e unita', unita'
  su ogni cifra isolata e nell'intestazione di colonna.
- **Decimali** da una funzione sola (`seo_titles.format_number`): euro sopra
  1.000 interi, percentuali e indici con un decimale, lo zero scritto "0", tre
  decimali sotto 0,01 e quattro sotto 0,001, perche' una cifra che zero non e'
  non si scrive "0,00". Le due copie (`numfmt.magnitude_decimals` e `decimals`
  di `v1.js`) le tiene allineate `tests/unit/test_decimals_parity.py`, e la
  stessa regola vale per scheda, pagine provincia e regione, ripieghi e gemelli
  Markdown. Si arrotonda in un punto solo, `it_numbers.number`, col cinque in
  su come `Intl.NumberFormat` del browser (26.348,5 fa 26.349): l'f-string di
  Python arrotonda al pari, e pagina e mappa si separavano su un pareggio. La preposizione davanti a una
  cifra ("dall'89,1%", "allo 0,2%", "dal 116%") la sceglie
  `numfmt.articulated`, e nessun altro.
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
