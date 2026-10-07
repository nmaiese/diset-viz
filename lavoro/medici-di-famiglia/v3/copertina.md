# Copertina v3: cure fuori regione

Articolo: `content/posts/2026-10-07-chi-eroga-cure-fuori-regione.md` (resta `draft: true`). Base: HEAD `e4317bea`. Dati personali: nessuno.

## Foto scelta

- File Commons: `File:Pavillon Francesco Ponti Polyclinique Milan - Milan (IT25) - 2022-09-02 - 2.jpg`
- Pagina: https://commons.wikimedia.org/wiki/File:Pavillon_Francesco_Ponti_Polyclinique_Milan_-_Milan_(IT25)_-_2022-09-02_-_2.jpg
- Autore: Chabe01 (opera propria, iPhone 13 Pro, 2022-09-02, Milano)
- Licenza: CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0 (riletta dall'API Commons `extmetadata`: nessuna restrizione dichiarata, uso commerciale ammesso)
- Originale 4032x3024, ritagliato a 1200x630 con fuoco 0.5,0.5. File: `app/static/img/blog/chi-eroga-cure-fuori-regione.jpg`, scheda `.photo.json`.

## Perché rappresenta il pezzo

Il pezzo mette la Lombardia al centro del confronto sui poli che attraggono cure da fuori regione. La foto mostra la facciata di un ospedale lombardo (padiglione Ponti del Policlinico di Milano) in modo letterale: un edificio ospedaliero, riconoscibile dalla scritta "Ospedale Policlinico", senza simboli generici. Non ritrae pazienti né persone. Non dice nulla su pubblico o privato: è un ospedale pubblico, quindi non va letta come illustrazione del "privato accreditato". Il `cover_alt` descrive solo ciò che si vede.

## Candidati considerati

Ricerca `photo search` con 6 query (ospedale Italia, ospedale Lombardia, Policlinico Milano, Sant'Orsola Bologna, ambulanza/pronto soccorso, hospital Italy building), 48 candidati con licenza ammessa, tutti guardati in anteprima.

- Scelto: n. 17, Policlinico di Milano, padiglione Ponti (frontale, luce buona, nessuna persona).
- Scartati vicini: n. 16 e n. 20 (stessa serie, prospettiva meno centrata o ritaglio più stretto); n. 10 Ariano Irpino (ospedale del Sud con eliporto, fuori dal territorio del pezzo); n. 21-22 elicottero di soccorso (suggerisce emergenza, non mobilità programmata); n. 42 Miulli e n. 43 Santa Lucia IRCCS (strutture private o IRCCS fuori dai poli del pezzo, e identificano un erogatore specifico); n. 33 Niguarda (cantiere/edificio moderno, inquadratura poco leggibile); i restanti sono ospedali storici, ex ospedali, targhe, ruderi o inquadrature laterali.
- Nessun candidato per l'Emilia-Romagna con foto adatta fra le query fatte. Per questo la foto rappresenta il polo lombardo e non il confronto: limite dichiarato.

## Verifica visiva del ritaglio

Ritaglio guardato a schermo. Facciata centrata, scritta "Ospedale Policlinico" leggibile in alto, ingresso con pensilina al centro, cielo in alto, selciato in basso. Nessuna persona, nessuna targa di auto. Cartelli sul lato sinistro del vialetto non leggibili. Bordi destro e sinistro tagliano le ali dell'edificio, accettabile.

## Esiti

- PIL: 1200x630, RGB, JPEG. OK.
- `git diff --check`: OK (solo avviso CRLF su `data/derived/casa_titolo_godimento.csv`, file non mio e non toccato).
- `bin/py -m unittest tests.integration.test_blog_trend_articles tests.integration.test_blog_indicator_links`: 23 test OK.
- Credito: `cover_credit` nel frontmatter identico al campo `cover_credit` di `.photo.json`.
- Guardia `scripts.trend_articles.verify` (anche `--offline`): 6 errori, **nessuno sulla copertina** (foto, scheda, licenza, credito non segnalati). Errori non legati alla copertina e lasciati come sono: manca `trend` (topic, detected, signals), manca il dossier `data/articles/chi-eroga-cure-fuori-regione/dossier.json`, e "media nazionale" senza dossier. Dipendono dal fatto che il pezzo non è passato dalla pipeline trend.

## Limiti

- La foto è un ospedale pubblico lombardo, non copre l'Emilia-Romagna né il tema pubblico/privato.
- Autore Chabe01 è un nome utente Commons, non un nome reale: va bene per CC BY-SA.
- Non ho aggiunto `cover_caption` (fuori dai tre campi richiesti).
- Anteprime in `data/articles/chi-eroga-cure-fuori-regione/photo-candidates/` non committate.
