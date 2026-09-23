#!/usr/bin/env bash
# I quattro pezzi del 23 settembre 2026: elaborazioni, dossier e figure.
# Si lancia dalla radice del repo. Rifa' tutto da capo a partire dalle fonti,
# cosi' ogni numero e ogni figura dei pezzi si puo' ricontrollare.
set -euo pipefail
PY="bin/py"
G="$PY -m scripts.articoli_trend.grafici"

# Elaborazioni (scaricano dalle fonti primarie)
$PY -m scripts.articoli_trend.elab_bes_ripartizioni SDG-311 SDG-310 01SAL005 03LAV007 SDG-405 12SER003 01SAL007
$PY -m scripts.articoli_trend.elab_mim_stranieri 201718 202425
$PY -m scripts.articoli_trend.elab_settori_infortuni
$PY -m scripts.articoli_trend.elab_media_province prov:07SIC008P 2021 2022 2023 --nome letalita_extraurbana_regioni
# data/elaborazioni/nsg_soccorso_2022.* e' una trascrizione dalla tabella 6a della Relazione NSG 2022.

S=scuola-media-competenze-nord-sud
$PY -m scripts.articoli_trend.dossier $S bes:SDG-311 ext:bes_ripartizioni_SDG-311 ext:mim_stranieri_terza_media ext:bes_ripartizioni_SDG-310 prov:02IST011P
$G $S linee ext:bes_ripartizioni_SDG-311 --con bes:SDG-311 --territori Liguria --titolo "Il Nord peggiora più in fretta del Sud" --nome italiano-2018-2025
$G $S dispersione ext:mim_stranieri_terza_media --con bes:SDG-311 --anni-x 2018,2025 --anni-y 2018,2025 --evidenzia Liguria,Marche,Sardegna,Umbria --titolo "Più alunni stranieri, più difficoltà? Solo in parte" --nome-x "alunni stranieri in terza media, punti in più" --nome-y "sotto la soglia in italiano, punti in più" --nome stranieri-competenze
$G $S barre bes:SDG-311 --riferimento ext:bes_ripartizioni_SDG-311 --evidenzia Sicilia,Liguria,Umbria --titolo "In Sicilia più di uno studente su due sotto la soglia" --nome italiano-regioni-2025

S=giovani-morti-in-strada-nord-sud
$PY -m scripts.articoli_trend.dossier $S bes:01SAL005 ext:bes_ripartizioni_01SAL005 ext:nsg_soccorso_2022 ext:letalita_extraurbana_regioni prov:07SIC008P
$G $S linee ext:bes_ripartizioni_01SAL005 --con bes:01SAL005 --territori Sardegna --titolo "Il Centro-Nord è sceso di più, e nel 2024 il Sud è sopra" --nome serie-2004-2024
$G $S barre bes:01SAL005 --riferimento ext:bes_ripartizioni_01SAL005 --evidenzia Sardegna,Calabria,Puglia --titolo "Nel 2024 la Sardegna è prima, con distacco" --nome regioni-2024
$G $S dispersione ext:nsg_soccorso_2022 --con ext:letalita_extraurbana_regioni --anni-x 2022 --anni-y 2023 --evidenzia Calabria,Basilicata,Sardegna,Emilia-Romagna --titolo "Soccorsi più lenti, incidenti più letali: un legame solo fra Nord e Sud" --nome-x "minuti per l'arrivo dei soccorsi, 2022" --nome-y "morti ogni 100 incidenti su strade extraurbane, 2021-2023" --sottotitolo "Tempo di arrivo dei mezzi di soccorso e letalità degli incidenti fuori dai centri abitati." --nome soccorsi-letalita

S=infortuni-lavoro-province
$PY -m scripts.articoli_trend.dossier $S prov:03LAV007 ext:bes_ripartizioni_03LAV007 ext:infortuni_attesi_settori ext:quota_occupati_agri_ind_costr bes:03LAV007
$G $S estremi prov:03LAV007 --quanti 10 --riferimento ext:bes_ripartizioni_03LAV007 --evidenzia Arezzo,Potenza,Milano --titolo "Il rischio più alto è nel centro Italia, il più basso nel Nord-Ovest" --nome province-2022
$G $S dispersione ext:quota_occupati_agri_ind_costr --con prov:03LAV007 --anni-x 2022 --anni-y 2022 --evidenzia Arezzo,Massa-Carrara,Perugia,Potenza,Mantova,Pavia,Verbano-Cusio-Ossola --titolo "I grandi settori spiegano poco" --nome-x "occupati in agricoltura, industria e costruzioni, %" --nome-y "infortuni gravi ogni 10.000 occupati" --sottotitolo "Quota di occupati nei settori più esposti e tasso di infortuni gravi, 2022." --nome settori-infortuni
$G $S linee ext:bes_ripartizioni_03LAV007 --titolo "Il Mezzogiorno scende più in fretta, ma resta sopra" --nome serie-2018-2022

S=alzheimer-cura-anziani-nord-sud
$PY -m scripts.articoli_trend.dossier $S bes:SDG-405 ext:bes_ripartizioni_SDG-405 ter:638 ext:bes_ripartizioni_12SER003 bes:12SER003
$G $S linee ext:bes_ripartizioni_SDG-405 --titolo "Il Centro è più vicino al Sud che al Nord" --nome posti-letto-2009-2023
$G $S barre ter:638 --evidenzia Campania,"Trentino Alto Adige",Lazio --titolo "In Trentino-Alto Adige 16 volte la Campania" --nome ospiti-anziani-2022
$G $S linee ext:bes_ripartizioni_12SER003 --titolo "L'assistenza a casa raddoppia ovunque" --nome adi-2015-2024
