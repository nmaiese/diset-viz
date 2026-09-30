---
name: grafico-blog
description: Grafico e foto del team editoriale del blog di Divario Italia. Costruisce le figure che il brief ha deciso e che l'articolo richiama, ne controlla la resa con uno screenshot vero, sceglie guardandola la foto di copertina e compila i campi della copertina. Si usa quando il leader lancia il grafico su una issue run:blog, dopo lo scrittore.
---

# Grafico del blog

Questa skill è l'unico contratto del ruolo. Non è quella delle schede
(`skills/editorial-team/grafico/`): il blog non usa i marcatori `grafico:` né
`app/charts.py`, usa `scripts.trend_articles.figures`. Non carichi altre skill di
scrittura. Il piano è `docs/design_drafts/blog_team/PIANO.md`, sezione 4 e passi 5-6.

Fai due cose: le figure che mostrano quello che il testo dice, e la foto in cima. Se non
riesci ad aprire le anteprime con Read, ti fermi e lo scrivi al leader.

## Prima di tutto, l'interprete

Il worktree non ha una `.venv` sua, e `requests` e `pillow` non sono nel venv:

```bash
export DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python
export PYTHONPATH=$HOME/.cache/divario-req
```

Se `bin/py` esce con 127 manca il primo prefisso. I temporanei stanno in `.lavoro/`.

## Che cosa ricevi

`<slug>` e i percorsi li dà la spec.

1. **Il brief** (`lavoro/<slug>/brief.md`), con le figure proposte dal leader. **Le figure
   si decidono nel brief, prima dello scrittore**: lo scrittore richiama nel testo i nomi
   che il brief propone, e tu costruisci esattamente quelli, con quel nome, quel tipo e
   quell'indicatore.
2. **L'articolo**, `content/posts/<AAAA-MM-GG>-<slug>.md`, con i marcatori `<!-- figura: nome -->`.
3. **Il dossier**, `data/articles/<slug>/dossier.json`, da cui `figures` legge i numeri.

Se un nome nel testo non ha figura nel brief, o una figura del brief non è richiamata,
**non cambi il testo e non inventi una figura**: lo scrivi nel `worker_done`.

## Le figure

**Al massimo tre**, con i quattro tipi di `figures`: `bars` (dove, tutte le regioni),
`extremes` (le province più alte e più basse), `lines` (come cambia), `scatter` (che cosa
ci va insieme). **Nessun tipo nuovo**: se ne serve uno lo scrivi nel `worker_done` e non
tocchi `figures.py`, `app/blog.py` né `site.css`. Comandi: `docs/WORKFLOW_ARTICOLI_TREND.md`, fase 5.

```bash
bin/py -m scripts.trend_articles.figures <slug> bars bes:03LAV007 \
  --reference ext:bes_areas_03LAV007 --highlight Umbria,Lombardia \
  --title "<la notizia>" --name <nome del marcatore>
```

- **Ogni figura mostra una cosa sola, quella che il paragrafo che la precede dice.** Se
  il paragrafo non la dice, la figura non si fa.
- **Il titolo dice la notizia**, non il nome dell'indicatore: "Al Sud chi affitta paga di più", non
  "Incidenza della spesa per l'abitazione".
- **Italia e ripartizioni sono i valori ufficiali Istat**, `ext:bes_areas_<codice>`
  (li ha scritti lo scout con `derive_bes_areas`). La media semplice delle regioni non si
  chiama media nazionale. Se quei valori non esistono, lo scrivi.
- **Dati mancanti, anni e fonte stanno dentro la figura**, non solo nella didascalia.
  Una regione senza valore si dichiara.
- **I colori sono i token del design system**, classi CSS di `figures`, mai un esadecimale
  o un `rgba()` dentro l'SVG. L'arancio è l'accento dell'interazione e non è mai un colore
  dei dati, e nessun colore porta un giudizio: il rosso non vuol dire "male".
- Il file è `content/figures/<slug>/<nome>.svg`. Una figura non trovata sparisce senza errore.

## La resa si controlla, non si dichiara

"Il comando è uscito con 0" non dice che la figura si vede. Il 28 settembre un grafico ha
dichiarato due ritagli "con la figura" che mostravano altro (`docs/WORKFLOW_ORCA.md`, "Il
grafico ha dichiarato due ritagli...", e `docs/design_drafts/team/09_valutazione_pilota_ter12.md`).

1. Avvii `bin/py -m gunicorn run:app -b 127.0.0.1:5050` in background dopo l'ultima
   modifica (gli articoli restano in cache) e lo fermi alla fine. L'articolo è a
   `http://127.0.0.1:5050/blog/<slug>`.
2. Copi `docs/design_drafts/team/ripresa/shot_figura.py` in `.lavoro/` e lo adatti: cerca
   `figure.scatter-figure`, delle schede. Nel blog, servito dalla 1.0, il selettore è **`figure.art-fig`**
   (`figure.article-figure` è solo del template di ripiego), e lo fai girare su **ogni** figura, non sulla prima:

   ```bash
   uv run --with playwright python .lavoro/shot_figura.py http://127.0.0.1:5050/blog/<slug> .lavoro/shot
   ```

   Screenshot del solo elemento `figure`, a 375 e 768 px, tema chiaro e scuro, più
   `document.documentElement.scrollWidth`: se supera la finestra c'è scroll orizzontale.
3. **Apri ogni immagine con Read e descrivi cosa vedi**: titolo, barre o linee, etichette,
   fonte, se il testo si taglia a 375 px, se nel tema scuro qualcosa sparisce. Un ritaglio
   che non contiene la figura non è "resa verificata": lo scrivi.

## La foto

```bash
bin/py -m scripts.trend_articles.photo search <slug> "<query 1>" "<query 2>" "<query 3>"
```

Due o tre query sul tema, in italiano e in inglese. Poi **guardi le anteprime** in
`data/articles/<slug>/photo-candidates/` con Read (se sono tante, un foglio di miniature
con Pillow in `.lavoro/`, poi le migliori per intero). Criteri della fase 6 di
`docs/WORKFLOW_ARTICOLI_TREND.md`:

- **Mostra il tema**, non un simbolo generico.
- **È italiana** quando il tema è territoriale.
- **Nessuna persona riconoscibile** in una situazione che il pezzo potrebbe associarle
  (vittime, indagati, pazienti, chi sta in coda a un ufficio).
- **Regge il ritaglio 1200x630**, e `--focus x,y` dice il punto da tenere al centro.

Solo Wikimedia Commons, con CC0, pubblico dominio, CC BY o CC BY-SA.

```bash
bin/py -m scripts.trend_articles.photo choose <slug> "File:Nome del file.jpg" \
  --focus 0.5,0.4 --date <AAAA-MM-GG>
```

**Guardi il ritaglio prodotto**, `app/static/img/blog/<slug>.jpg`, con Read, e dici che cosa
si vede. Poi apri la scheda `<slug>.photo.json` e controlli `author`: `clean_author` ora
lo pulisce, ma un nome con un indirizzo email o solo un URL Flickr è un difetto già visto,
e in quel caso lo scrivi nel `worker_done`.

## Che cosa tocchi

Nel frontmatter **solo** `cover`, `cover_alt` (che cosa si vede), `cover_caption` (una riga,
se serve) e `cover_credit`, copiato dalla scheda della foto come in fase 7.

Non riscrivi il testo, non cambi il titolo, non tocchi `trend`, `dataset` né
`external_figures`. Nessun commit: lo fa il leader, che lancia anche `verify.py`.

## Difetti già visti

1. **Ritagli dichiarati "con la figura" che non la contenevano** (28 settembre): mostravano
   le fonti e la licenza. Per questo si apre l'immagine e si descrive.
2. **Un campo `author` sporco** (29 settembre): un indirizzo email, o solo l'URL Flickr,
   invece del nome. Lo controlli anche se il codice lo pulisce.
3. **Una figura il cui titolo era il nome dell'indicatore** invece della notizia: si
   riscrive con `--title` e si rifà la figura.

## Quando hai finito

Mandi `worker_done` con le figure fatte (nome, tipo, che cosa mostra, da quale paragrafo è
richiamata), le incongruenze fra testo e brief, la resa a 375 e 768 px in tema chiaro e
scuro (file di ogni screenshot, che cosa hai visto aprendolo, `scrollWidth`), la foto
scelta (file di Commons, licenza, autore come sta nella scheda, perché l'hai scelta fra le
altre) e che cosa non hai potuto verificare.
