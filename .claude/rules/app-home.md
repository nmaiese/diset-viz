---
paths:
  - "app/design/pages/home.py"
  - "app/home_pick.py"
  - "app/templates/v1/home.html"
  - "app/templates/v1/home/**"
  - "app/static/js/ds-home.js"
  - "app/static/js/home-map.js"
  - "app/views.py"
  - "tests/**/test_home_*.py"
---

# La home: le regole che non si vedono rompendole

- `/` — la home, **server-rendered** (`app/templates/v1/home.html` con un
  partial per fascia in `app/templates/v1/home/`, e `home.html` come ripiego):
  la testata con la ricerca e la mappa per andare a una regione, nei colori
  della qualita' della vita (`home.hero_map`, profilo predefinito, con la sua
  legenda; senza classifica torna la mappa grigia). Sotto i 600 pixel la mappa
  non si disegna e al suo posto, dopo le porte, c'e' la lista dei punteggi in
  un `<details>` (`home-map-values`), con i territori non valutati;
  le porte del sito; un indicatore in evidenza **diverso a ogni visita**
  (`app/home_pick.py`, per regione o per provincia), con tutti e due i livelli
  nello stesso pannello quando tutti e due stanno nel pool; regioni e province
  con un territorio estratto a caso e l'anteprima della sua scheda; la fascia
  "Gli indicatori, tema per tema" (`#temi`), che e' la porta dell'atlante; la
  qualita' della vita come porta, senza classifica; le storie; in fondo una
  riga sola con fonti, metodo, come citare e correzioni (dal 28 settembre 2026
  il quiz e la fascia delle fonti non sono piu' fasce della home: il quiz si
  raggiunge dalla porta Giochi). Per questo **non sta nella cache di pagina**: rimetterci
  `@cache.cached` mostrerebbe lo stesso indicatore e gli stessi territori a
  tutti per cinque minuti. Le anteprime dei territori
  (`home.territory_previews`) escono dalle stesse funzioni delle pagine
  regione e provincia e si calcolano una volta per processo: costano circa
  un secondo alla prima home di ogni istanza. `?indicatore=<codice>&livello=`
  fissa la scelta (e `?indicator=<id>` del selettore di prima) se quella coppia
  sta nel pool, se no si torna al caso. Il canonico resta `/`. Non e'
  l'atlante. La fascia `#temi` (dal 25 settembre 2026) ha un solo bottone
  primario, "Esplora i N indicatori nell'atlante", con N dalle righe regionali
  dell'atlante (`atlante.rows("regione")["total"]`), che porta sempre alle
  regioni; il selettore Regioni/Province di `_feature.html` con id propri
  (`temi-*`, perche' `tab-regione` e `lv-regione` sono dell'indicatore in
  evidenza); i conteggi d'area verso `/atlante?area=<nome intero dell'area>`
  (con `livello=provincia` sulle province), il valore che `atlante.js`
  confronta con `data-atlas-area`; e per ogni area l'indicatore cambiato di
  piu' (`home.atlas_band`, `synchronized_cache`): variazione della media
  semplice sul pannello fisso divisa per lo scarto interquartile dei territori
  nell'ultimo anno, fra le righe indicizzabili con la linea, regola scritta
  nella riga fonte. Il pannello Province ha solo quello, senza testa e coda.
  La fascia si calcola fuori da `design.render` (`_home_atlas_band`, come
  `_home_feature_pick`): se cede, restano le schede delle regioni di prima
  invece del ripiego della pagina intera. Non costa niente a freddo, perche'
  la proiezione la scalda gia' `home_pick`. Il gemello Markdown ha la stessa
  sezione.
