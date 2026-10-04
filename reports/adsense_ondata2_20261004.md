# AdSense ondata 2, fix P1 (4 ottobre 2026)

- Fotografia GSC spostata in `config/indicator_search_metrics.csv` (git mv) e spedita nell'immagine con una COPY dedicata; la regola ora avvisa con `logging.warning` se il file manca, ma fallisce aperta.
- Differenza di conteggio: 57 schede in classe b, la sitemap perde 56 base + 5 `/province` = 61 URL.
- La 57ª, `bes:01SAL001` (speranza di vita alla nascita), non era in sitemap neanche prima: scheda a due livelli, il livello base regionale non passava già `all_bes_indicators` (copertura), c'era solo la sua vista `/province`.
- Commit: `0b55cff8`.
