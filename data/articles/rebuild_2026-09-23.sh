#!/usr/bin/env bash
# I quattro pezzi del 23 settembre 2026: elaborazioni, dossier e figure.
# Si lancia dalla radice del repo. Rifa' tutto da capo a partire dalle fonti,
# cosi' ogni numero e ogni figura dei pezzi si puo' ricontrollare.
set -euo pipefail
PY="bin/py"
DAY=2026-09-23
F="$PY -m scripts.trend_articles.figures"
D="$PY -m scripts.trend_articles.dossier"

# Elaborazioni (scaricano dalle fonti primarie)
$PY -m scripts.trend_articles.derive_bes_areas SDG-311 SDG-310 01SAL005 03LAV007 SDG-405 12SER003 01SAL007
$PY -m scripts.trend_articles.derive_foreign_pupils 201718 202425
$PY -m scripts.trend_articles.derive_sector_injuries
$PY -m scripts.trend_articles.derive_province_mean prov:07SIC008P 2021 2022 2023 --name extraurban_lethality_regions
# data/derived/emergency_response_2022.* e' una trascrizione dalla tabella 6a della Relazione NSG 2022.

S=scuola-media-competenze-nord-sud
$D $S bes:SDG-311 ext:bes_areas_SDG-311 ext:foreign_pupils_grade8 ext:bes_areas_SDG-310 prov:02IST011P --date $DAY
$F $S lines ext:bes_areas_SDG-311 --with bes:SDG-311 --territories Liguria --title "Il Nord peggiora più in fretta del Sud" --name italiano-2018-2025
$F $S scatter ext:foreign_pupils_grade8 --with bes:SDG-311 --years-x 2018,2025 --years-y 2018,2025 --highlight Liguria,Marche,Sardegna,Umbria --title "Più alunni stranieri, più difficoltà? Solo in parte" --name-x "alunni stranieri in terza media, punti in più" --name-y "sotto la soglia in italiano, punti in più" --name stranieri-competenze
$F $S bars bes:SDG-311 --reference ext:bes_areas_SDG-311 --highlight Sicilia,Liguria,Umbria --title "In Sicilia più di uno studente su due sotto la soglia" --name italiano-regioni-2025

S=giovani-morti-in-strada-nord-sud
$D $S bes:01SAL005 ext:bes_areas_01SAL005 ext:emergency_response_2022 ext:extraurban_lethality_regions prov:07SIC008P --date $DAY
$F $S lines ext:bes_areas_01SAL005 --with bes:01SAL005 --territories Sardegna --title "Il Centro-Nord è sceso di più, e nel 2024 il Sud è sopra" --name serie-2004-2024
$F $S bars bes:01SAL005 --reference ext:bes_areas_01SAL005 --highlight Sardegna,Calabria,Puglia --title "Nel 2024 la Sardegna è prima, con distacco" --name regioni-2024
$F $S scatter ext:emergency_response_2022 --with ext:extraurban_lethality_regions --years-x 2022 --years-y 2023 --highlight Calabria,Basilicata,Sardegna,Emilia-Romagna --title "Soccorsi più lenti, incidenti più letali: un legame solo fra Nord e Sud" --name-x "minuti per l'arrivo dei soccorsi, 2022" --name-y "morti ogni 100 incidenti su strade extraurbane, 2021-2023" --subtitle "Tempo di arrivo dei mezzi di soccorso e letalità degli incidenti fuori dai centri abitati." --name soccorsi-letalita

S=infortuni-lavoro-province
$D $S prov:03LAV007 ext:bes_areas_03LAV007 ext:injuries_expected_by_sector ext:employment_share_agri_ind_constr bes:03LAV007 --date $DAY
$F $S extremes prov:03LAV007 --count 10 --reference ext:bes_areas_03LAV007 --highlight Arezzo,Potenza,Milano --title "Il rischio più alto è nel centro Italia, il più basso nel Nord-Ovest" --name province-2022
$F $S scatter ext:employment_share_agri_ind_constr --with prov:03LAV007 --years-x 2022 --years-y 2022 --highlight Arezzo,Massa-Carrara,Perugia,Potenza,Mantova,Pavia,Verbano-Cusio-Ossola --title "I grandi settori spiegano poco" --name-x "occupati in agricoltura, industria e costruzioni, %" --name-y "infortuni gravi ogni 10.000 occupati" --subtitle "Quota di occupati nei settori più esposti e tasso di infortuni gravi, 2022." --name settori-infortuni
$F $S lines ext:bes_areas_03LAV007 --title "Il Mezzogiorno scende più in fretta, ma resta sopra" --name serie-2018-2022

S=alzheimer-cura-anziani-nord-sud
$D $S bes:SDG-405 ext:bes_areas_SDG-405 ter:638 ext:bes_areas_12SER003 bes:12SER003 --date $DAY
$F $S lines ext:bes_areas_SDG-405 --title "Il Centro è più vicino al Sud che al Nord" --name posti-letto-2009-2023
$F $S bars ter:638 --highlight Campania,"Trentino Alto Adige",Lazio --title "In Trentino-Alto Adige 16 volte la Campania" --name ospiti-anziani-2022
$F $S lines ext:bes_areas_12SER003 --title "L'assistenza a casa raddoppia ovunque" --name adi-2015-2024

# La classifica del giorno si ricalcola dai segnali e dall'interesse salvati.
$PY -m scripts.trend_articles.rank --day $DAY > /dev/null
