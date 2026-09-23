# Articoli guidati dai trend

Come si passa da **che cosa si cerca oggi in Italia** a un articolo del blog
che dia a quella ricerca il contesto dei dati: un indicatore completo, con
grafici, fonti, metodo e una foto vera con licenza.

Questo documento possiede il processo. Gli strumenti stanno in
`scripts/articoli_trend/`, uno per fase, e la mappa dei temi in
`config/trend_temi.json`. Non usa la catena della redazione
(`nmaiese/redazione-ai`): e' un canale diverso, piu' corto, per un altro tipo
di pezzo. La catena scrive la prosa delle **schede indicatore**
(`content/indicators/`), che restano la risposta di riferimento a "che cos'e'
questo dato". Questo workflow scrive **articoli del blog** (`content/posts/`)
che rispondono a "perche' se ne parla oggi, e che cosa dicono i dati".

## Il principio

Un pezzo nasce solo se ci sono **tutte e due** le cose: un interesse di
ricerca vero e attuale, e un dato solido con una storia dentro. Tanto
interesse su un dato debole produce un pezzo che non regge. Un dato ottimo
che nessuno cerca produce un pezzo che nessuno legge. La classifica
(fase 3) esiste per rendere questa scelta esplicita e ricontrollabile.

E vale il vincolo del sito: **niente prodotto cartesiano** province x
indicatori. Si scrive dove c'e' una storia (un outlier, un'inversione, un
divario che si apre o si chiude), **al massimo 8 pagine nuove a settimana**.

## Le fasi

Tutti i comandi si lanciano dalla radice del repo, con `bin/py`.

| fase | strumento | produce |
| --- | --- | --- |
| 1. segnali | `raccogli` | `data/trend/<giorno>/segnali.json` |
| 2. interesse | `interesse` (con uv) | `data/trend/<giorno>/interesse.json` |
| 3. classifica | `classifica` | `data/trend/<giorno>/classifica.{json,md}` |
| 4. dossier | `dossier` | `data/articoli/<slug>/dossier.json`, `app/static/data/articoli/<slug>.csv` |
| 5. grafici | `grafici` | `content/figure/<slug>/*.svg` |
| 6. foto | `foto cerca` / `foto scegli` | `app/static/img/blog/<slug>.jpg` e `.foto.json` |
| 7. scrittura | chi redige | `content/posts/<data>-<slug>.md` |
| 8. verifica | `verifica` | esito, errori e avvisi |
| 9. pubblicazione | PR, merge umano | il pezzo in produzione |

### 1. Segnali: che cosa si cerca e di che cosa si parla

```bash
bin/py -m scripts.articoli_trend.raccogli
```

Legge, senza chiavi e da fonti aperte:

- **Google Trends, ricerche di tendenza per l'Italia** (feed RSS
  `trends.google.com/trending/rss?geo=IT`): le ricerche che stanno salendo
  adesso, con traffico approssimato e le notizie collegate.
- **Google News Italia**: le notizie principali del giorno, e per ogni tema
  della mappa la ricerca degli ultimi sette giorni (`when:7d`).
- **Istat, pubblicazioni recenti** (feed del sito, senza i bandi di gara). Un
  dato appena uscito e' un trend: e' il giorno in cui qualcuno lo cerca.

Ogni segnale e' salvato com'e' arrivato, con fonte, URL e data. Ai segnali si
abbinano i temi di `config/trend_temi.json` con parole intere (`rsa` non si
accende in `borsa`). Il file si committa: e' la prova del perche'.

Il feed delle tendenze e' dominato da sport, spettacolo e cronaca: e' normale.
Quello che conta per questo sito e' la parte che tocca un tema con un dato,
e le tendenze di cronaca sono spesso l'aggancio migliore (un incidente,
un'allerta meteo, un furto). **Ma una tendenza che il testo abbina a un tema
va letta**: il titolo di una notizia collegata puo' contenere la parola giusta
per la ragione sbagliata.

### 2. Interesse: quanto si cerca, se cresce, dove

```bash
~/.local/bin/uv run --no-project --with pytrends --with "urllib3<2" \
    --with pandas python -m scripts.articoli_trend.interesse
```

Per ogni query di ogni tema: la **crescita** (ultimi 7 giorni sugli 83
precedenti), il **livello** rispetto a un'ancora fissa ("pensioni", perche' ogni
richiesta a Google Trends e' normalizzata a 100 sul suo massimo e due temi si
confrontano solo passando per la stessa ancora), e l'interesse **per
regione** negli ultimi 7 giorni.

`pytrends` non e' una dipendenza del sito e non deve diventarlo: gira in un
ambiente usa-e-getta. E' lento apposta (una pausa fra le richieste) e fa
anche 30 minuti per tutta la mappa: si lancia in background, oppure solo su
alcuni temi con `--temi`. Se Google risponde 429 riprova; se fallisce, il
tema resta senza misura e la classifica ridistribuisce il peso sugli altri
segnali, **non** lo tratta come zero. Il ripiego va scritto nel rapporto.

**Sono indici relativi, non volumi.** Nel testo non si scrive mai "N
ricerche". Si puo' scrivere che un tema e' piu' cercato del solito, o in
quali regioni lo e' di piu', citando Google Trends e la finestra.

Al primo giro l'ancora era "meteo" ed era troppo forte: il livello di tutti i
temi usciva zero e la classifica si e' retta su notizie e crescita. Un'ancora
deve stare nello stesso ordine di grandezza dei temi che misura.

### 3. Classifica: dal tema all'indicatore

```bash
bin/py -m scripts.articoli_trend.classifica
```

Per ogni coppia tema-indicatore della mappa, tre punteggi fra 0 e 1, ognuno
con la motivazione scritta accanto:

- **interesse**: notizie dei 7 giorni che confermano il tema, presenza fra le
  tendenze o le notizie principali di oggi, crescita e livello su Trends;
- **dato**: recenza dell'ultimo anno, copertura (province meglio di regioni),
  profondita' della serie;
- **storia**, calcolata dai valori: un outlier, un'inversione di tendenza, un
  divario Mezzogiorno/Centro-Nord che si allarga o si stringe, un record.

Totale = interesse x (dato + storia) / 2. Una coppia si scarta se l'interesse
e' sotto 0,25 o il dato sotto 0,5. La classifica e' un ordine di lettura, non
una decisione: **chi sceglie legge le prime righe e i segnali che le
sostengono**, e scarta un tema quando il segnale e' spurio o quando il pezzo
non aggiungerebbe niente a una scheda che gia' c'e'. Prima di scegliere,
controllare in `content/posts/` che l'argomento non sia gia' stato scritto:
in quel caso si aggiorna il pezzo esistente (campo `updated`), non se ne
scrive un secondo.

**Limite noto del punteggio "storia".** Quasi ogni indicatore territoriale ha
un outlier da qualche parte, quindi il punteggio sta spesso vicino a 1 e
distingue poco. Serve a scartare le coppie senza storia, non a ordinare
quelle che ce l'hanno: l'ordine lo fanno interesse e dato. La soglia
dell'outlier (oggi z >= 1,8) va rivista dopo qualche giornata di classifiche.

Aggiungere un tema: una voce in `config/trend_temi.json` con le parole, le
query, gli indicatori e le query per le foto. Un tema senza un indicatore del
sito non entra: e' il sito che da' il contesto, non la notizia.

### 4. Dossier: tutti i numeri, con la loro provenienza

```bash
bin/py -m scripts.articoli_trend.dossier <slug> bes:03LAV007 prov:03LAV007
```

Il primo indicatore e' il principale, gli altri sono i parenti (lo stesso
dato a un altro livello, o un indicatore imparentato per il confronto). Il
dossier contiene per ognuno: fonte, archivio, unita', anni, la scheda
canonica sul sito (chiesta all'app, non indovinata), la classifica
dell'ultimo anno, la serie, le medie per anno e le variazioni, e **l'elenco
delle cifre ammesse nel testo**, gia' scritte come compariranno. Scrive anche
il CSV scaricabile del pezzo.

I numeri vengono dai dataset che il sito serve (`app/static/data/`), che
portano gia' fonte e archivio Istat riga per riga: un numero nel pezzo e' lo
stesso numero che il lettore trova nella scheda.

**Le medie del dossier sono medie semplici dei territori**, non pesate per
popolazione. Non sono la media nazionale e non si chiamano cosi'. Se il
pezzo ha bisogno del valore Italia, lo prende dalla pubblicazione Istat e lo
dichiara fra le `cifre_esterne`, con URL.

### 4b. Contesto e prova delle tesi

Un dossier con i numeri giusti non basta. Prima di scrivere, per ogni pezzo:

1. **Chi ne ha già scritto.** Rapporti delle fonti (Istat, Invalsi, Inail, Iss),
   lavoce.info, Openpolis, Info Data, centri di ricerca. Se ne ricavano i
   concetti, con parole nostre e citando chi li ha proposti, e si cerca
   l'angolo che nessuno ha coperto.
2. **Valori ufficiali, non medie semplici.** Per Italia, Nord, Centro e
   Mezzogiorno si usano i valori calcolati dall'Istat
   (`elab_bes_ripartizioni`), che pesano la popolazione. La media semplice
   delle regioni sbaglia: sui posti letto il Centro (60 per 10.000) spariva
   dentro un "Centro-Nord" a 97.
3. **Le ipotesi alternative, con i dati.** Ogni tesi causale ("il Nord peggiora
   perché ci sono più alunni stranieri") si mette alla prova con un indicatore
   che la possa smentire, in un'elaborazione versionata in
   `data/elaborazioni/` con `method` e script (`elab_mim_stranieri`,
   `elab_settori_infortuni`, `elab_media_province`). Il grafico di dispersione
   salva le correlazioni in `data/articoli/<slug>/legame_*.json`, **anche
   dentro ciascun gruppo**: un legame che esiste solo fra Nord e Sud può
   dipendere da qualunque cosa distingua le due aree, e va scritto così.
4. **Quello che non regge si scrive.** Un test che fallisce è un'informazione
   per il lettore, non un pezzo da tagliare.
5. **Fact-check avversariale.** Chi scrive non referta: prima della PR ogni
   pezzo passa dall'agent `fact-checker`, con il dossier e le copie delle
   fonti. I suoi rilievi alti si correggono tutti.

Il 23 settembre 2026 questo passaggio ha cambiato le tesi di tutti e quattro i
pezzi: le ipotesi di partenza (stranieri, settori, famiglie, soccorsi) erano
tutte parzialmente sbagliate o non dimostrabili.

### 5. Grafici

```bash
bin/py -m scripts.articoli_trend.grafici <slug> dispersione ext:X --con bes:Y --anni-x 2018,2025 --anni-y 2018,2025 --titolo "..." --nome legame
bin/py -m scripts.articoli_trend.grafici <slug> barre   bes:03LAV007 --evidenzia Umbria,Lombardia --titolo "..." --nome classifica
bin/py -m scripts.articoli_trend.grafici <slug> estremi prov:03LAV007 --quanti 10 --titolo "..." --nome province
bin/py -m scripts.articoli_trend.grafici <slug> linee   bes:03LAV007 --territori Umbria --titolo "..." --nome serie
```

Tre forme, perche' tre sono le domande: **dove** (barre, tutte le regioni
con la media semplice come riferimento), **gli estremi** (le province piu'
alte e piu' basse, senza stampare 107 barre), **come cambia** (linee, con
Centro-Nord e Mezzogiorno e i territori di cui il testo parla).

Le figure sono SVG in linea, che l'articolo richiama con
`<!-- figura: nome -->` su una riga sua. I colori sono classi CSS sui token
del design system (`site.css`, sezione "Le figure degli articoli del blog"),
quindi seguono il tema scuro e nessun colore e' cotto nel file. Il titolo
della figura **dice la notizia**, non il nome dell'indicatore. Titolo,
unita', anno e fonte stanno dentro la figura. Accessibilita': `<title>` e
`<desc>` con i valori estremi, le linee si distinguono per tratto oltre che
per colore, e le etichette stanno in fondo alla linea invece che in legenda.

### 6. Foto

```bash
bin/py -m scripts.articoli_trend.foto cerca  <slug> "cantiere edile" "construction site Italy"
bin/py -m scripts.articoli_trend.foto scegli <slug> "File:Nome del file.jpg" --fuoco 0.5,0.4
```

**Solo fotografie vere, con una licenza che ne permetta l'uso.** Niente
immagini generate, niente illustrazioni, niente foto prese da un giornale.

La fonte e' **Wikimedia Commons**: la sua API restituisce autore, licenza e
URL della licenza in forma leggibile da una macchina, quindi l'attribuzione
non la copia a mano nessuno. Sono ammesse CC0, pubblico dominio, CC BY e
CC BY-SA. `cerca` scarta il resto, scarta i file che non sono foto (mappe,
loghi, grafici, disegni, scansioni) e quelli troppo piccoli, e salva le
anteprime in `data/articoli/<slug>/foto-candidate/`. **Le anteprime vanno
guardate**: la pertinenza la decide un occhio, non una query. Criteri:
- la foto mostra il tema, non un simbolo generico, e non ritrae una persona
  riconoscibile in una situazione che il pezzo potrebbe associarle (vittime,
  indagati, pazienti);
- e' italiana quando il tema e' territoriale;
- regge il ritaglio 1200x630 (`--fuoco` dice quale punto tenere al centro).

`scegli` scarica l'originale, ritaglia, salva il JPG e la **scheda della
foto** (`<slug>.foto.json`): file, pagina originale, autore, licenza con URL,
modifiche fatte. Il campo `cover_credit` del pezzo si copia dalla scheda, e
la pagina lo mostra sotto la foto come "Foto: autore, licenza, via Wikimedia
Commons. Ritagliata e ridimensionata." La CC BY-SA sulla foto non si estende
al testo dell'articolo: la foto e' usata cosi' com'e', solo ritagliata.

Unsplash e Pexels sono un ripiego ammesso quando Commons non ha niente di
adatto: licenze proprie che permettono l'uso senza attribuzione obbligatoria,
ma si attribuisce lo stesso, e serve una chiave API. La scheda della foto si
compila allo stesso modo, a mano, con l'URL della pagina della foto.

### 7. Scrittura

Il pezzo va in `content/posts/<AAAA-MM-GG>-<slug>.md`. Voce e regole sono
quelle di [`content/STYLE.md`](../content/STYLE.md), senza eccezioni: niente
`—`, `–`, `;`, `…`, le "Tecniche da giornalista" e l'imperfezione concessa
nella forma e vietata nel contenuto. Struttura (REVIEW.md, passaggio 2):

1. **l'aggancio**: la notizia o la ricerca di questi giorni, detta in una
   frase, con la conseguenza per chi vive li'. E' il motivo per cui il pezzo
   esiste oggi;
2. **il dato che da' il contesto**, con la cifra che il lettore porta via;
3. **dove**: il confronto fra territori, con la figura;
4. **come cambia**: la serie, con la figura;
5. **un confronto con un indicatore imparentato**;
6. **"Dati usati"**: fonte, periodo, territorio, unita', metodo e limite;
7. **"## Fonti"**: ogni fonte esterna citata nel testo, con data.

Il frontmatter, oltre ai campi del blog:

```yaml
cover: /static/img/blog/<slug>.jpg
cover_alt: "Descrizione di cio' che si vede nella foto"
cover_caption: "Una riga su che cosa mostra la foto, se serve."
cover_credit:            # copiato da <slug>.foto.json
  autore: "..."
  licenza: "CC BY-SA 4.0"
  licenza_url: "https://creativecommons.org/licenses/by-sa/4.0"
  fonte_url: "https://commons.wikimedia.org/wiki/File:..."
  fonte_nome: "Wikimedia Commons"
  modifiche: "Ritagliata e ridimensionata"
indicator: bes-03LAV007  # obbligatorio: aggancia il pezzo alla scheda
trend:                   # perche' questo pezzo, oggi
  tema: sicurezza-lavoro
  rilevato: 2026-09-23
  classifica: data/trend/2026-09-23/classifica.json
  punteggio: {interesse: 0.9, dato: 0.8, storia: 1.0}
  segnali:
    - tipo: google_news_principali
      testo: "titolo della notizia"
      fonte: "Google News Italia"
      url: "https://..."
      data: 2026-09-22
dataset:                 # lo schema Dataset della pagina
  name: "..."
  description: "..."
  method: "Medie semplici dei territori, non pesate..."
  temporal: "2018/2022"
  spatial: "Italia, regioni e province"
  creator: "Istat"
  source_url: "https://esploradati.istat.it/..."
  download: /static/data/articoli/<slug>.csv
cifre_esterne:           # ogni numero che non viene dal dossier
  - cifra: "1.090"
    cosa: "morti sul lavoro denunciate nel 2024"
    fonte: "Inail, Relazione annuale 2025"
    url: "https://..."
```

Il campo `trend` non si vede in pagina: e' la tracciabilita' della scelta.
Il blocco `dataset` diventa lo schema `Dataset` (licenza, metodo, copertura,
download) e il riquadro "I dati di questo articolo" in fondo al pezzo.

### 8. Verifica

```bash
bin/py -m scripts.articoli_trend.verifica content/posts/<file>.md
```

Ferma il pezzo su: frontmatter incompleto (trend, dataset, credito foto),
foto senza scheda o con licenza non ammessa, credito diverso dalla scheda,
caratteri vietati, **una cifra che non sta nel dossier ne' fra le
`cifre_esterne`**, "media nazionale" detta di una media semplice, un link
interno che non risponde 200, una fonte citata nel testo che non risponde o
che manca dalla sezione "## Fonti", una figura senza file. Gli avvisi (un
piccolo numero che non e' nel dossier, piu' di mille parole) si leggono.

Poi la suite: `bin/py -m unittest discover -s tests -v`. I test
`tests/integration/test_blog_articoli_trend.py` controllano credito foto,
figure e `Dataset` su tutti i pezzi.

La verifica automatica non legge il senso. Prima della PR una seconda
lettura, di chi non ha scritto il pezzo, controlla quello che una guardia non
vede: che la definizione dell'indicatore sia detta giusta
(`bin/py scripts/definition_check.py --show bes-03LAV007`), che il nesso fra
la notizia e il dato non sia forzato, che nessuna causa sia attribuita a un
dato che non la mostra.

### 9. Pubblicazione

Un ramo per pezzo o per gruppo di pezzi della stessa giornata, PR verso
`master` con nel corpo, per ogni pezzo: il trend d'origine, la classifica
(le prime righe e i temi scartati, con il motivo), le figure, la foto con la
licenza. **Il merge e' la pubblicazione ed e' umano** (REVIEW.md). Niente
push, PR o deploy senza il via libera di chi possiede il sito.

## Cadenza

Il giro completo (fasi 1-3) si puo' lanciare ogni mattina: sono dieci minuti
per i segnali e la classifica, mezz'ora in background per Trends. Il file del
giorno resta anche quando non se ne ricava un pezzo: una serie di giornate
dice quali temi tornano, ed e' da li' che si decide che cosa aggiungere alla
mappa. Tetto: 8 pagine nuove a settimana, e un tema non torna prima di un
mese salvo un fatto nuovo nei dati.
