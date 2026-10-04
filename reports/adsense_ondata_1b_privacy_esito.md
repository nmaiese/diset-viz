# Ondata 1/1b AdSense: esito del fix privacy (commit f47ff3fe)
Fatto: firma del riquadro «Dati e metodo» = costante `REDAZIONE` («Redazione Divario
Italia») in app/dati_metodo.py, non piu' editor_name; test del box aggiornati. Tolto
il nome da reports/adsense_ondata_1b_esito.md, docs/GIOCO.md e da un commento in
app/indicator_view.py. Nuovo tests/unit/test_privacy_nome.py: legge `git ls-files` negli
ambiti app/, content/, config/, docs/GIOCO.md, reports/adsense_ondata_1*.md e fallisce
se trova il nome fuori da config/identita.yaml, privacy e `ECCEZIONI_IN_ATTESA_IDENTITA`
(publisher.py + template che stampano editor_name).
grep del nome proprio (cognome e nome completo) sugli ambiti del test
-> solo app/publisher.py:45 (eccezione dichiarata); config/identita.yaml non esiste qui.
Test verdi: box (unit+integration), test_privacy_nome, test_v1_pages + test_ads_policy (31).
Suite unit 744: restano i 4 failure + 1 errore preesistenti (PIL su photo/verify), nessuna regressione.
Restano occorrenze del nome di battesimo in documenti interni fuori ambito, non corretti:
DEPLOY.md 4, REVIEW.md 3, STATUS.md 20, docs/*.md 18 (totale 45).
