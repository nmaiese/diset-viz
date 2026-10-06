# Esperimento sull'indicizzazione delle regioni (6/20)

Stato al 6 ottobre 2026. La diagnosi sta in `orca/direzione/review/diagnosi-indicizzazione-regioni-2026-10-05.md` (fuori dal repo): 14 regioni su 20 sono «scansionate ma attualmente non indicizzate» e nessuna causa tecnica spiega perché.

## Che cosa si prova
Su due regioni non indicizzate, **Molise** e **Valle d'Aosta**, le tabelle dei 157 indicatori e quella delle altre fonti stanno in un `details` chiuso, con un `summary` che dice cosa contiene e quante righe (commit `75b50804`, costante `REGIONI_TABELLE_CHIUSE` in `app/design/pages/regione.py`). Il contenuto resta nell'HTML. Le altre 18 regioni escono come prima.

**Limite da dire chiaro:** la pagina pesa ancora circa 380-390 KB e le parole nel codice sono le stesse. L'esperimento cambia ciò che si vede (la pagina si apre su prosa e grafici invece che su 234 righe di tabella), non il peso. Distingue «forma percepita» da «peso»; **non** prova né smentisce l'ipotesi del peso. Se non si muove nulla, il passo due è ridurre davvero l'HTML (tabelle caricate a richiesta), con un secondo esperimento.

Le due regioni scelte coprono i due casi della diagnosi: Valle d'Aosta ha molto testo proprio (12 paragrafi), Molise meno.

## Gruppo di controllo
Le altre 12 regioni non indicizzate al 5 ottobre (Abruzzo, Basilicata, Campania, Friuli-Venezia Giulia, Lazio, Liguria, Marche, Piemonte, Puglia, Sardegna, Umbria, Veneto), invariate. Elenco verificato sul censimento del 5/10: sono tutte «scansionata, ma attualmente non indicizzata», come le due prove.

## Come si misura
- **Prima:** censimento del 5 ottobre (`url_inspection_2026-10-05_160.json`): Molise e Valle d'Aosta «Pagina scansionata, ma attualmente non indicizzata», ultima scansione 24 settembre, cioè prima dell'esperimento.
- **Dopo:** stesso comando e stesso seme, `scripts/misure/url_inspection.py --per-tipo 20 --max 160 --seme 1`, **il 19 ottobre** (primo controllo) e **il 26 ottobre** (conferma). Dalla risposta si leggono, per le 20 regioni, `coverageState` e `lastCrawlTime`.
- **Validità:** il confronto conta solo se `lastCrawlTime` di Molise e Valle d'Aosta è successivo al 6 ottobre (Google ha rivisto la pagina nuova). Se non è successivo, il risultato non dice nulla: si aspetta o si chiede la scansione in Search Console, e si scrive.
- **Esito:** segnale positivo se almeno una delle due passa a «Inviata e indicizzata» o «Scansionata e indicizzata» e nel controllo non più di una regione si muove allo stesso modo. Con due pagine contro dodici è un indizio, non una prova: non si decide un cambio a tutto il sito su questo solo dato.
- **Annullare:** svuotare `REGIONI_TABELLE_CHIUSE`.

## Cosa non si fa nel frattempo
Né `noindex` sulle regioni, né riscrittura delle 20 pagine, né altre modifiche a Molise e Valle d'Aosta (cambierebbero l'esperimento).
