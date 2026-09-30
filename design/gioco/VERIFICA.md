# Verifica del sotto-marchio del gioco (30 settembre 2026)

Le prove fatte sul ramo `nmaiese/gioco-identita`, con le uscite vere.

## I token: `bin/py design/v1/tools/check_tokens.py`

Sui valori committati, coda dell'uscita:

```
  ok   light --game-* di system.css uguali a tokens.json
  ok   dark --game-* di system.css uguali a tokens.json

tutte le soglie reggono
exit 0
```

Con `game.light.accent` spostato sul `seq-4` della rampa (tokens.json alterato e
poi ripristinato):

```
  NO   light game-accent su bg: 3.95
  NO   light game-accent su surface-1: 3.65
  NO   light game-accent su surface-2: 3.40
  NO   light game-accent su game-wash: 3.50
  NO   light game-on-accent su game-accent (bottone di gioco): 3.95
  NO   light game-accent dalla rampa blu: 0 gradi
  NO   light game-accent dal colore dei dati piu' vicino (seq-4): 0.000
  NO   light --game-* di system.css uguali a tokens.json: diversi [('accent', '#4383c8'), ('accent', '#9c29d0')]
8 soglie saltate
exit 1
```

Le stesse prove in memoria, un token sbagliato alla volta (`check()` su una copia del JSON):

```
game-accent = seq-4 (blu dei dati): 8 soglie saltate
   NO light game-accent su bg: 3.95
   NO light game-accent su surface-1: 3.65
   NO light game-accent su surface-2: 3.40
   NO light game-accent su game-wash: 3.50
   NO light game-on-accent su game-accent (bottone di gioco): 3.95
   NO light game-accent dalla rampa blu: 0 gradi
   NO light game-accent dal colore dei dati piu' vicino (seq-4): 0.000
   NO light --game-* di system.css uguali a tokens.json: diversi [('accent', '#4383c8'), ('accent', '#9c29d0')]
game-accent = arancio del sito: 5 soglie saltate
   NO dark game-accent (tinta 55) dall'arancio: 0 gradi
   NO dark game-accent dal verde e dal rosso: 29 gradi (error)
   NO dark game-accent dal colore dei dati piu' vicino (accent): 0.000
   NO dark game-accent contro game-wrong, visione peggiore: 0.018
   NO dark --game-* di system.css uguali a tokens.json: diversi [('accent', '#d48af8'), ('accent', '#ef852e')]
game-accent verde: 3 soglie saltate
   NO light game-accent dal verde e dal rosso: 6 gradi (success)
   NO light game-accent contro game-right, visione peggiore: 0.017
   NO light --game-* di system.css uguali a tokens.json: diversi [('accent', '#1f7a4a'), ('accent', '#9c29d0')]
game-wrong = game-right: 6 soglie saltate
   NO light game-right contro game-wrong, normale: 0.000
   NO light game-right contro game-wrong, protan: 0.000
   NO light game-right contro game-wrong, deutan: 0.000
   NO light game-right contro game-wrong, tritan: 0.000
   NO light game-right contro game-wrong, acroma: 0.000
   NO light --game-* di system.css uguali a tokens.json: diversi [('wrong', '#1d7635'), ('wrong', '#6c1614')]
game-wrong scuro chiaro come il giusto: 2 soglie saltate
   NO dark game-right contro game-wrong, deutan: 0.102
   NO dark --game-* di system.css uguali a tokens.json: diversi [('wrong', '#e47c75'), ('wrong', '#f08a80')]
```

## Le quattro visioni

Distanze in OKLab dopo la simulazione (Machado 2009 a severita' piena,
acromatopsia come grigio a pari luminanza). Soglie: giusto contro sbagliato
0,12 in ogni visione, azione di gioco contro giusto e sbagliato 0,10 nelle tre
carenze (non in acromatopsia, dove l'azione si distingue per forma e testo).

| tema | coppia | normale | protan | deutan | tritan | acroma |
|---|---|---|---|---|---|---|
| light | game-right / game-wrong | 0.263 | 0.242 | 0.140 | 0.270 | 0.176 |
| light | success / error del sito | 0.269 | 0.133 | 0.040 | 0.298 | 0.045 |
| light | game-accent / game-right | 0.368 | 0.273 | 0.235 | 0.193 | 0.003 |
| light | game-accent / game-wrong | 0.305 | 0.326 | 0.288 | 0.198 | 0.173 |
| dark | game-right / game-wrong | 0.290 | 0.249 | 0.141 | 0.315 | 0.181 |
| dark | success / error del sito | 0.261 | 0.119 | 0.015 | 0.284 | 0.044 |
| dark | game-accent / game-right | 0.332 | 0.281 | 0.212 | 0.212 | 0.136 |
| dark | game-accent / game-wrong | 0.184 | 0.192 | 0.183 | 0.117 | 0.045 |

Il verde e il rosso del sito stanno a 0,040 e 0,015 in deuteranopia e a 0,045
in scala di grigi: per questo il gioco ha `--game-right` e `--game-wrong`
propri, separati anche in luminosita'.

**Il compromesso da decidere.** L'accento rispetta la regola della spec (tinta a
100 gradi dall'arancio e a 60 dalla rampa, in visione normale). Sotto
protanopia e deuteranopia pero' un viola magenta scivola verso il blu: dalla
rampa sta a 0,078 in chiaro e 0,033 in scuro, cioe' il difetto per cui era
stato scartato il viola della ricerca, attenuato ma non tolto. La ricerca sulle
tinte (tutte, a passi di 2 gradi) mostra che nessuna tinta sta a 0,10 da tutti
i colori dei dati in tutte le visioni: la rampa blu occupa un lato, arancio,
ocra, verde e rosso l'altro. La difesa e' d'uso: l'accento del gioco non va mai
su una mappa o un grafico coi dati. Se non basta, l'alternativa e' un accento
a bassa croma o neutro, e il gioco perde il suo colore.

## Nessun colore scritto nei fogli del gioco

```
$ grep -nE '#[0-9a-fA-F]{3,8}\b|rgba?\(' frontend/src/game/*.css
(nessuna riga, uscita 1)
$ bin/py -m unittest tests.unit.test_css_tokens
Ran 11 tests ... OK
```

I tre test nuovi (colori, `--game-*` definiti nei due temi, movimento solo
dietro `no-preference`) falliscono se in `guess.css` si aggiunge una regola con
`#fff`, `transition` e `var(--game-nope)`: provato e ripristinato.

## Il prototipo

Chrome headless via CDP su `file://.../design/gioco/index.html`, con
`prefers-reduced-motion: reduce`:

| larghezza | tema | scrollWidth / clientWidth | font caricati | --game-accent |
|---|---|---|---|---|
| 390 | chiaro | 390 / 390 | Sofia Sans, Sofia Sans Semi Condensed | #9c29d0 |
| 390 | scuro | 390 / 390 | Sofia Sans, Sofia Sans Semi Condensed | #d48af8 |
| 1280 | chiaro | 1280 / 1280 | Sofia Sans, Sofia Sans Semi Condensed | #9c29d0 |
| 1280 | scuro | 1280 / 1280 | Sofia Sans, Sofia Sans Semi Condensed | #d48af8 |

Guardato a occhio: la sfida del giorno in evidenza (fondo tenue, filo spesso a
sinistra, bottone pieno), le tre schede con le icone a 34 pixel, i nove
traguardi a 24 con lo stato scritto, la tabella degli indizi (a 390 le
etichette vanno a capo e le cifre restano allineate), i suggerimenti, i due
tentativi sbagliati con l'icona, il filo e la parola, la mappa col tratteggio
sulle due province provate. Corretti dopo la prima occhiata: le schede
dell'hub ereditavano la sottolineatura di `.ds a`, i suggerimenti avevano il
bordo nativo del bottone.

## Cosa non e' provato

- Chi e' maggiore?, Ordina le regioni e la classifica non sono stati resi dopo
  la divisione dei fogli: il prototipo usa solo le classi dell'hub e di
  Indovina. `.qz-hero`, `.crown`, il podio e le righe di Ordina sono da
  guardare nel sito servito. Nessun selettore di primo livello compare in due
  dei quattro fogli, quindi l'ordine nuovo non dovrebbe cambiare la cascata.
- Il moto normale (`no-preference`) non e' stato guardato: gli screenshot sono
  col moto ridotto.
- Sulla mappa vera del gioco il giusto e lo sbagliato restano distinti dal
  solo riempimento: il tratteggio sta in `proto.css`, perche' la mappa viene
  dal template (`_italy_map.html`), che questo lavoro non tocca.
- La suite unitaria intera: 499 test, 11 fallimenti e 1 errore, tutti per
  `requests` assente dal venv (`test_trend_articles_cli`, `test_foto_autore`),
  estranei al gioco.

## Il nome

Tre proposte in `README.md`: **Divario in gioco** (segnaposto nel prototipo),
**Sfida Italia**, **Il Quiz del Divario**.
