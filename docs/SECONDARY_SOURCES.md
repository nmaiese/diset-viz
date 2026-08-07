# Il registro delle fonti secondarie

Le fonti da cui un articolo indicatore puo' prendere **contesto**, e solo
contesto. Il numero di base viene sempre dalla serie primaria che la pagina gia'
mostra, e la fonte secondaria serve a tre cose: dire che cosa ha detto
l'istituzione quando ha pubblicato quel dato, portare un confronto europeo o
storico che la nostra serie non copre, e reggere un claim comparativo che
altrimenti andrebbe tagliato.

Esiste perche' senza un elenco chi scrive parte da una ricerca a freddo, e una
ricerca a freddo su un tema statistico italiano restituisce prima gli aggregatori
e i blog che le fonti. Qui ci sono solo istituzioni, e una riga per capire in un
colpo d'occhio se la fonte serve a questo articolo.

**Un URL di questo elenco va comunque aperto prima di citarlo.** Il registro dice
dove guardare, non che cosa c'e' scritto oggi. Una citazione senza URL verificato
si taglia, e una fonte inventata e' l'unico errore da cui non si torna indietro.

## La trappola che passa tutte le guardie

Quasi tutte queste fonti pubblicano **aggregati ponderati**, nazionali o di
ripartizione. Le nostre pagine calcolano la **media semplice dei valori
regionali**. Non sono la stessa grandezza, e nessuna guardia della suite se ne
accorge, perche' l'aritmetica delle due cifre e' corretta separatamente.

Quindi: se citi un dato nazionale, scrivi "dato nazionale <fonte>" e tienilo
staccato dalla "media semplice delle regioni". Non affiancarli come se uno
confermasse l'altro, e non usare la nostra media per dire "in Italia".

## Il registro

**Il registro vive in `data/corpus/sources.json`, non qui.** Questa pagina lo
descriveva con una tabella, e una tabella e' una seconda copia: il giorno che
qualcuno aggiunge una fonte in un posto solo, i due elenchi divergono senza che
niente fallisca. E' la forma di deriva che questo progetto ha gia' pagato.

Per leggerlo:

```bash
python3 -c "import json;[print(f\"{s['id']:32}{s['institution']:52}{s['citability']}\") for s in json.load(open('data/corpus/sources.json'))]"
```

Citabilita': **aperta** riuso libero con attribuzione, **report** PDF gratuito
citabile per numero e pagina, **attenzione** parte a pagamento o presso terzi.

## Il corpus: le citazioni gia' verificate

Il registro dice *dove guardare*. Il corpus dice *che cosa c'e' scritto*, ed e'
la novita': `data/corpus/claims/`, un file per affermazione, ognuna con il
proprio identificatore, il testo **verbatim**, l'URL e la data di lettura.

Esiste perche' il difetto peggiore degli articoli non era un errore, era il
freddo: potevano descrivere solo la geometria della serie, mai perche' si
muove. La causa non si inventa, si cita, e un'affermazione con un
identificatore e' una causa che si puo' controllare.

Due regole, e sono assolute.

- **Verbatim, non parafrasi.** `python3 -m scripts.fetch_corpus --verify`
  riscarica ogni URL con la sola libreria standard e cerca la citazione come
  stringa. Nessun modello nel giro di verifica, perche' il rischio da cui
  difendersi e' proprio un modello che riassume mentre copia. Alla prima prova
  ha bocciato una citazione su due: il testo era vero, ma stava su un'altra
  pagina di quello stesso sito e aveva perso l'incipit.
- **Ogni sezione che racconta una dinamica porta almeno un identificatore.**
  Controllo posizionale, non lessicale: cercare i connettivi causali non
  funziona, perche' nei 375 articoli sono quasi tutti definitori ("dipende dal
  denominatore") mentre la causalita' vera viaggia senza connettivi ("si e'
  chiusa dal basso, pero', non dall'alto").

### Il tema e' una cartella, non una pertinenza

Un'affermazione dichiara i `themes` a cui si applica, e per un po' e' bastato.
Non basta: nella prima run del workflow la stessa citazione Eurostat sulla
sensibilita' ciclica della **disoccupazione di lunga durata** e' finita sia sul
tasso di disoccupazione sia sul **tasso di attivita'**, perche' condividono il
tema "Lavoro e conciliazione". Sul secondo era forzata, e una citazione forzata
e' peggio di nessuna citazione: e' vera, verificabile, e non spiega quello che
sembra spiegare.

Da qui il campo facoltativo **`chiavi`**: una lista di parole che devono
comparire nel nome dell'indicatore perche' l'affermazione arrivi per tema.

```json
{ "id": "eurostat-lunga-durata-ciclo",
  "themes": ["Lavoro e conciliazione"],
  "chiavi": ["disoccupazione", "disoccupati"] }
```

Un'affermazione che nomina l'indicatore in `indicators` **non passa dalle
chiavi**: e' gia' pertinente per dichiarazione. Un'affermazione che vale per
tutto un tema non le dichiara e continua a valere per tutto il tema. Le chiavi
si aggiungono quando ci si accorge che una citazione e' andata dove non doveva,
cioe' **leggendo una pagina**, che resta l'unico modo per trovare questa
classe di errore.

**Modificare un'affermazione puo' bloccare articoli gia' pubblicati.** Il lint
ha una regola bloccante, `fonte-non-pertinente`, per un identificatore che
esiste nel corpus ma non e' offerto a quell'indicatore: aggiungere `chiavi` a
un'affermazione gia' citata la rende non pertinente **a posteriori**. E' voluto,
perche' un'attribuzione falsa non diventa vera col tempo. Ma vuol dire che dopo
ogni modifica a un file di `data/corpus/claims/` si esegue

```bash
bin/py -m officina.lint
```

e si riparano gli articoli che il cambio ha reso scoperti. Le chiavi sono un
confronto per sottostringa sul **nome** dell'indicatore: `disoccupazione` prende
"tasso di disoccupazione" e non prende "quota di occupati". Man mano che il
corpus cresce, scegliere chiavi troppo strette blocca articoli buoni e troppo
larghe non protegge da niente.

Gli URL del registro sono stati verificati uno per uno con una richiesta reale
il 26 luglio 2026. Le citazioni del corpus si riverificano invece a comando, e
ognuna porta la propria data di lettura.

**Due host rispondono 403 a una richiesta automatica** e non sono per questo
morti: OpenCoesione e OECD bloccano gli user agent non browser. Se WebFetch
torna 403 su quei due, non e' una fonte da scartare, e' un blocco: cerca il
documento specifico invece della home, oppure cita l'istituzione a partire da un
PDF raggiungibile. Non trattare un 403 come "fonte inesistente", perche' il
riflesso giusto altrove ("se non la apro la taglio") qui taglia una fonte buona.

## Come si usa, in pratica

1. Guarda il tema dell'indicatore nel brief e apri **una o due** voci pertinenti.
   Non e' una rassegna stampa, e tre fonti in un pezzo da 600 parole sono troppe.
2. Cerca una cosa sola: qualcosa che il cruscotto non puo' dire. Il commento
   dell'istituto sull'ultimo movimento, la posizione italiana in Europa, un
   caveat di definizione, un controesempio.
3. Verifica l'URL, poi scrivilo in `fonti` come `{testo, url}`, con un `testo`
   che dice che cosa quella fonte sostiene, non solo il suo nome.
4. Se non trovi niente di pertinente, non citare niente. Una fonte messa li' per
   riempire il campo e' peggio del campo vuoto.
