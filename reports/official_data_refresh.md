# Monitoraggio fonti dati ufficiali

Questo file viene aggiornato solo quando cambia almeno un artefatto ufficiale.

## Stato integrato

- Atlante regionale: 393 indicatori, 62 con ultimo anno 2025 o 2026, massimo 2026.
- Qualità della vita regionale: 145 indicatori BES con dati regionali, 67 al 2025, massimo 2025.
- Province: restano sul BES dei Territori 2025 finché Istat non pubblica la nuova edizione.

## Artefatti monitorati

| fonte | URL | ultima modifica HTTP | sha256 |
|---|---|---|---|
| Indicatori territoriali Istat | https://www.istat.it/storage/politiche-sviluppo/Archivio_unico_indicatori_regionali.zip | Fri, 17 Jul 2026 07:02:57 GMT | `36ba03030cd3ee5f2d2742abf3677ae825f838419e9ba4eb520e0b719a3e2830` |
| BES nazionale, regioni | https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip | Mon, 25 May 2026 15:00:11 GMT | `9003db40394edeb2c88bfa6b6fb56a176c6c00f7e24897b4f5d9af5db40cbebc` |

## Regole automatiche

- Un hash diverso avvia la rigenerazione dei dataset e dei manifest.
- I test bloccano schema, copertura, direzioni e regressioni del punteggio.
- Il workflow apre una pull request: i cambi di definizione o copertura non entrano in produzione senza una revisione leggibile.
- Le serie non confrontabili restano contestuali e non entrano nello scoring.
