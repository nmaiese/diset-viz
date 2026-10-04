# AdSense ondata 2, esito del 4 ottobre 2026

## Classificazione

- Fotografia Search Console: 28 giorni al 3 ottobre 2026, 411 schede.
- Classe a: 229 schede con prosa e impressioni.
- Classe b: 57 schede senza prosa e senza impressioni.
- Classe c: 30 schede con piu' impressioni, sovrapposta alla classe a.
- Altre: 106 con prosa senza impressioni, 19 con impressioni senza prosa.
- La classe b resta sotto la soglia di arresto di 150 schede.

## Modifica

- Le 57 schede di classe b servono `noindex, follow` ed escono dalla sitemap.
- Una scheda rientra automaticamente quando riceve un lead o un corpo di sezione scritto.
- Schede con impressioni restano invariate anche senza prosa.
- CSV versionato: `reports/adsense_indicator_classification_20261003.csv`.

## Verifica

- `bin/py scripts/adsense_audit.py --timeout 10`: exit 0, rapporto 20261004 scritto.
- Pesi contro 20261003: quattro pagine identiche, home da 953,0 a 954,5 KB stimati.
- PageSpeed senza chiave: HTTP 429, limite dichiarato nel rapporto di audit.
- Test policy e coerenza sitemap: 6 test, OK.
- Test integration toccati e contratti collegati: 225 test, OK.
- Suite unit: 736 test, 4 failure e 1 errore per `PIL` assente nei moduli foto e verify.
- `git diff --check`: OK.
