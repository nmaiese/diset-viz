# Ondata 1b AdSense: esito (riquadro "Dati e metodo" e regola annunci)

Fatto: un riquadro solo, `app/templates/v1/_dati_metodo.html` (macro `dm.box`), su indicatore, provincia, regione, tema, qualita' della vita (basi) e articolo. Fonte con link, data di aggiornamento solo se `publisher.dataset_updated` la registra, limite del confronto, firma di `editor_name` e link a `/metodologia`. Niente HTML copiato, niente date inventate. La regola annunci e' `app/ads_policy.ads_allowed(page, word_count)`: vera solo per `blog` e pagine >= 500 parole, falsa per interfacce (atlas, search, game, account, legacy, error) e sotto soglia; documentata in `docs/ADSENSE.md`, nessuna unita' inserita.

Esempio reso per tipo (blocco `aside.dati-metodo`):
- indicatore: `Fonte: Istat, Conti economici territoriali.` `Fonte aggiornata il 17 luglio 2026.` `La media è una media semplice non ponderata...` `A cura di Aniello Maiese. Metodologia`
- provincia: `Fonte: Istat, benessere e qualità della vita.` `Fonte aggiornata il 25 maggio 2026.` `Non è una classifica ufficiale...` `A cura di Aniello Maiese. Metodologia`
- regione: `Fonte: Istat, indicatori territoriali.` `Fonte aggiornata il 17 luglio 2026.` `Le posizioni descrivono, non spiegano...` `A cura di Aniello Maiese. Metodologia`
- tema: `Fonte: Istat, indicatori territoriali.` `Fonte aggiornata il 17 luglio 2026.` `Il punteggio non pesa gli indicatori per importanza...` `A cura di Aniello Maiese. Metodologia`
- qualita-della-vita: `Fonte: Istat, benessere e qualità della vita.` `Fonte aggiornata il 25 maggio 2026.` `Non è la classifica del Sole 24 Ore...` `A cura di Aniello Maiese. Metodologia`
- articolo: `Fonte: Istat.` `L'analisi confronta territori di peso diverso...` `A cura di Aniello Maiese. Metodologia` (senza data: la fonte dell'articolo non la registra)

Test: unit 743 (4 failure + 1 errore preesistenti, manca PIL su modulo photo/verify; 18 nuovi verdi), integration toccati tutti verdi (`test_dati_metodo`, `test_v1_pages`, `test_app`, `test_ads_policy`, e gli altri). Resta fuori: la suite intera segfaulta in `test_app.py` sul caricamento immagini (CPython 3.13 "Executing a cache", preesistente, non di questa ondata).
