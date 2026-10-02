# Report di Estrazione Dati: ACI e AGCOM

## 1. Fonte ACI (Automobile Club d'Italia, Autoritratto 2025)

- **File sorgente**: `lavoro/cache/Parco_veicolare_2025.xlsx` (estratto da `Autoritratto2025_Parco_veicolare.zip`).
- **Licenza**: Creative Commons CC-BY 4.0 (`https://aci.gov.it/attivita-e-progetti/studi-e-ricerche/open-data/`).
- **Indicatori estratti**:
  1. `ACI_AUTO_ANTE_2009`: Quota di autovetture immatricolate fino al 2009 (% sul totale autovetture). Direzione: `lower_better`.
  2. `ACI_AUTO_ALIMENTAZIONE_ALTERNATIVA`: Quota di autovetture con alimentazione diversa da benzina e gasolio (% sul totale autovetture). Direzione: `higher_better`.
- **Copertura territoriale**: 107 province su 107 (100%), 20 regioni su 20 (100%).
- **Anni**: 2025 (stock al 31/12/2025). Verificate le edizioni precedenti (2024, 2023, 2020): l'edizione 2024 presenta classi d'anno differenti (`FINO AL 2008`), mentre le edizioni precedenti hanno strutture di foglio differenti. Pertanto la serie per `ACI_AUTO_ANTE_2009` è limitata al 2025 per coerenza di definizione.
- **Valori noti verificati**:
  - `ACI_AUTO_ANTE_2009`: Trento 13,9% (basso), Biella 39,6% (medio), Catania 60,0% (alto).
  - `ACI_AUTO_ALIMENTAZIONE_ALTERNATIVA`: Nuoro 5,5% (basso), Siena 18,0% (medio), Firenze 34,6% (alto).
- **Output prodotti**:
  - `scripts/nuovi_dati/aci.py`
  - `app/static/data/nuovi/aci.csv` (254 righe)
  - `app/static/data/nuovi/aci_manifest.csv`
  - `tests/unit/test_nuovi_aci.py`

## 2. Fonte AGCOM (Broadband Map, 4T 2025)

- **File sorgente**: `lavoro/cache/Survey_Italy_IT_DESI_2026_Data_2025_v2_pub.xlsx` e `RapportoAggiornamentoBBmap_4Q25vs4Q24_r260119.pdf`.
- **Licenza**: Creative Commons CC-BY 4.0 (`https://geo.agcom.it/`).
- **Indicatore estratto**:
  1. `AGCOM_FTTH`: Famiglie raggiunte dalla rete in fibra FTTH (%). Direzione: `higher_better`. Tema: `Società dell'informazione`.
- **Copertura territoriale**: 20 regioni su 20 (100%), 105 province su 107.
- **Province escluse**: Bolzano (`bolzano`) e Trento (`trento`), escluse a causa della lacuna di rilevazione dichiarata nelle note metodologiche generali del report AGCOM ("mancata o incompleta trasmissione dei dati degli operatori locali").
- **Anni**: 2025 (4° trimestre 2025).
- **Valori noti verificati**:
  - Regioni: Valle d'Aosta 58,63% (basso), Piemonte 73,20% (medio), Sicilia 89,06% (alto).
  - Province: Massa-Carrara 73,51% (medio), Palermo 95,14% (alto).
- **Output prodotti**:
  - `scripts/nuovi_dati/agcom.py`
  - `app/static/data/nuovi/agcom.csv` (125 righe)
  - `app/static/data/nuovi/agcom_manifest.csv`
  - `tests/unit/test_nuovi_agcom.py`
