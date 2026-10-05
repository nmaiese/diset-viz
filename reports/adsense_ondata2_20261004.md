# AdSense ondata 2, fix P1 (4 ottobre 2026)

- Fotografia GSC spostata in `config/indicator_search_metrics.csv` (commit `0913c52a`, per git un rename senza modifiche di contenuto) e spedita nell'immagine con una COPY dedicata; la regola ora avvisa con `logging.warning` se il file manca, ma fallisce aperta.
- Differenza di conteggio: 57 schede in classe b, la sitemap perde 56 base + 5 `/province` = 61 URL.
- La 57ª, `bes:01SAL001` (speranza di vita alla nascita), non era in sitemap neanche prima: scheda a due livelli, il livello base regionale non passava già `all_bes_indicators` (copertura), c'era solo la sua vista `/province`.
- Commit sul ramo: `1fc78831` (audit A2), `25fe67eb` (regola AdSense), `0913c52a` (CSV in `config/` e COPY nel Dockerfile), `026aba14` (questo rapporto), `0303560b` (test allineati alla classe b).
