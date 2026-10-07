# Numeri e pre-registrazione

## Fonti del calcolo e separazione dal sondaggio

Ipotesi esplorative H1 e H2, non prove. Ho ricalcolato variazioni, ranghi medi e medie in aritmetica decimale dalle 360 celle regionali del CSV Istat locale `app/static/data/Assoluti_BES_Regione.csv`, con chiavi `idIndicatore`, `Territorio`, `Anno`, `Livello/Variazione`, `Dato`. Ho riconciliato le stesse 360 celle, sei indicatori, 20 regioni e anni 2019, 2023 e 2025, con l'appendice Istat ufficiale 2026: 360/360 identiche. Toscana e Campania incluse.

Ricalcolo indipendente riproducibile: `DIVARIO_PYTHON=/home/nilo/.local/bin/python bin/py lavoro/furti-sicurezza-percepita/ricalcolo.py` dalla radice del repository. Lo script legge il CSV, non questo documento.

Unità: furti per 1.000 famiglie; borseggi e rapine per 1.000 abitanti; rischio, degrado e sicurezza percepita in percentuale. Sono popolazioni e unità diverse. I livelli BES dei furti/borseggi/rapine stimano vittime e correggono il sommerso secondo la definizione Istat. Non confrontare i loro livelli direttamente con denunce provinciali per 100.000 residenti.

## Formula e chiavi

- Universo: le 20 chiavi di regione condivise dalle matrici per ciascun anno richiesto. Trentino-Alto Adige è una singola unità regionale. N=20, salvo rimozioni dichiarate.
- Variazione: `x[regione, anno_finale] - x[regione, anno_iniziale]`, senza ponderazione.
- Divergente H1: `delta_furti < 0 AND delta_rischio > 0`. Esiti esattamente zero non contano come aumento o calo.
- Spearman: Pearson sui ranghi medi in presenza di ex aequo, formula `corr(rank(x), rank(y))`. Non sono p-value, non sono test inferenziali, non correggono selezione multipla.
- Medie riportate: media aritmetica semplice delle 20 variazioni o valori regionali, non media nazionale ponderata.

## H1, 2023-2025

N=20. Divergenza in **8/20**: Emilia-Romagna, Friuli-Venezia Giulia, Lazio, Molise, Piemonte, Sardegna, Toscana, Umbria. Media semplice furti: 7,38 a 6,86 per 1.000 famiglie, delta -0,52. Media semplice rischio: 18,83% a 22,61%, delta +3,78 punti. Sono medie regionali non ponderate, non valori italiani.

Spearman tra livelli 2025 furti e rischio: ρ=0,634586466 (N=20). Tra le variazioni 2023-2025: ρ=-0,001129518 (N=20). L'associazione dei livelli territoriali non descrive quella tra cambiamenti.

Esclusione di Toscana e Campania fissata prima del calcolo: N=18, divergenze 7/18, ρ furti/rischio=0,103359187. Il segno opposto compare ancora in sette regioni, ma il coefficiente cambia; non è una prova di tenuta. Toscana: furti 14,8→12,6, rischio 20,5→27,8, rapine 1,4→1,2. Campania: furti 6,2→5,5, rischio 39,0→38,0, rapine 1,5→1,1. Le unità restano diverse.

| Regione | Furti 2023 | Furti 2025 | Δ furti | Rischio 2023 | Rischio 2025 | Δ rischio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Abruzzo | 7.7 | 7.9 | +0.2 | 18.4 | 19.2 | +0.8 |
| Basilicata | 3.2 | 2.9 | -0.3 | 14.0 | 11.3 | -2.7 |
| Calabria | 3.2 | 2.2 | -1.0 | 10.7 | 10.3 | -0.4 |
| Campania | 6.2 | 5.5 | -0.7 | 39.0 | 38.0 | -1.0 |
| Emilia-Romagna | 10.1 | 9.6 | -0.5 | 21.4 | 25.5 | +4.1 |
| Friuli-Venezia Giulia | 8.9 | 8.2 | -0.7 | 13.3 | 20.3 | +7.0 |
| Lazio | 9.9 | 7.0 | -2.9 | 32.8 | 35.8 | +3.0 |
| Liguria | 5.3 | 5.3 | +0.0 | 17.8 | 22.6 | +4.8 |
| Lombardia | 9.7 | 9.8 | +0.1 | 25.8 | 32.8 | +7.0 |
| Marche | 7.5 | 8.0 | +0.5 | 14.5 | 18.7 | +4.2 |
| Molise | 6.5 | 4.1 | -2.4 | 11.5 | 22.2 | +10.7 |
| Piemonte | 7.5 | 7.4 | -0.1 | 19.7 | 25.8 | +6.1 |
| Puglia | 5.9 | 5.4 | -0.5 | 25.3 | 24.6 | -0.7 |
| Sardegna | 3.0 | 2.7 | -0.3 | 10.3 | 12.9 | +2.6 |
| Sicilia | 4.9 | 3.5 | -1.4 | 22.4 | 19.0 | -3.4 |
| Toscana | 14.8 | 12.6 | -2.2 | 20.5 | 27.8 | +7.3 |
| Trentino Alto Adige | 5.7 | 6.8 | +1.1 | 12.0 | 18.8 | +6.8 |
| Umbria | 12.6 | 11.5 | -1.1 | 23.1 | 32.5 | +9.4 |
| Valle d'Aosta | 4.1 | 5.1 | +1.0 | 4.5 | 7.9 | +3.4 |
| Veneto | 10.9 | 11.7 | +0.8 | 19.6 | 26.2 | +6.6 |

## H1 finestra alternativa 2019-2025

N=20. Divergenza in 11/20 regioni: Campania, Lazio, Liguria, Lombardia, Molise, Piemonte, Puglia, Sardegna, Toscana, Trentino Alto Adige, Umbria. Spearman tra variazioni furti/rischio ρ=0,107802495. Senza Toscana e Campania: N=18, divergenza 9/18, ρ=0,148109808. Media semplice 2019→2025 furti: 9,380→6,860, Δ=-2,520. Rischio: 22,095→22,610, Δ=+0,515. Arrotondato a due decimali, 22,095 è 22,10. La media semplice del rischio è al minimo nel 2023 soltanto fra i tre anni confrontati, non nella serie: la serie disponibile 2005-2025 tocca il minimo nel 2021. Toscana: furti 18,1→12,6, rischio 25,9%→27,8%. Campania: 7,0→5,5 e 36,4%→38,0%. La Campania diverge anche nella finestra lunga, quindi il contrasto direzionale con la Toscana vale solo nel 2023-25.

| Regione | Furti 2019 | Furti 2025 | Δ furti | Rischio 2019 | Rischio 2025 | Δ rischio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Abruzzo | 9.3 | 7.9 | -1.4 | 21.6 | 19.2 | -2.4 |
| Basilicata | 4.0 | 2.9 | -1.1 | 12.8 | 11.3 | -1.5 |
| Calabria | 5.5 | 2.2 | -3.3 | 19.0 | 10.3 | -8.7 |
| Campania | 7.0 | 5.5 | -1.5 | 36.4 | 38.0 | +1.6 |
| Emilia-Romagna | 14.0 | 9.6 | -4.4 | 26.6 | 25.5 | -1.1 |
| Friuli-Venezia Giulia | 8.2 | 8.2 | +0.0 | 15.0 | 20.3 | +5.3 |
| Lazio | 10.3 | 7.0 | -3.3 | 35.1 | 35.8 | +0.7 |
| Liguria | 8.6 | 5.3 | -3.3 | 21.3 | 22.6 | +1.3 |
| Lombardia | 11.1 | 9.8 | -1.3 | 26.4 | 32.8 | +6.4 |
| Marche | 10.5 | 8.0 | -2.5 | 26.5 | 18.7 | -7.8 |
| Molise | 6.5 | 4.1 | -2.4 | 15.6 | 22.2 | +6.6 |
| Piemonte | 11.6 | 7.4 | -4.2 | 23.2 | 25.8 | +2.6 |
| Puglia | 8.9 | 5.4 | -3.5 | 23.3 | 24.6 | +1.3 |
| Sardegna | 5.3 | 2.7 | -2.6 | 12.6 | 12.9 | +0.3 |
| Sicilia | 7.5 | 3.5 | -4.0 | 23.8 | 19.0 | -4.8 |
| Toscana | 18.1 | 12.6 | -5.5 | 25.9 | 27.8 | +1.9 |
| Trentino Alto Adige | 8.9 | 6.8 | -2.1 | 12.4 | 18.8 | +6.4 |
| Umbria | 16.4 | 11.5 | -4.9 | 29.9 | 32.5 | +2.6 |
| Valle d'Aosta | 4.5 | 5.1 | +0.6 | 11.9 | 7.9 | -4.0 |
| Veneto | 11.4 | 11.7 | +0.3 | 22.6 | 26.2 | +3.6 |

## H2, misure incrociate e controlli contrari

La matrice sotto incrocia sei misure su tutte le 20 regioni: furti, rischio percepito, rapine, borseggi, degrado e percezione di sicurezza. Le ultime quattro rispondono al controllo H2. Non sono popolazioni o unità omogenee. Variazioni indicate in unità originali: pp per percentuali, valori per 1.000 per reati.

H2 selezionando i soli otto territori divergenti 2023-25: degrado cresce in 8/8 (+1,64 punti di media semplice), percezione di sicurezza diminuisce in 8/8 (-6,68 punti). Il controllo contrario è il gruppo non divergente: degrado cresce già in 10/12 e sicurezza cala in 11/12. Quindi il segnale percettivo non è specifico delle otto regioni, e non spiega il motivo del divario. Rapine aumentano in 4/8, borseggi aumentano in 4/8: supporto misto, da conservare. Intero campione: degrado sale in 18/20, sicurezza scende in 19/20, rapine salgono in 6/20 e borseggi in 6/20.

| Regione | Furti 23→25 | Rischio 23→25 | Rapine 23→25 | Borseggi 23→25 | Degrado 23→25 | Sicurezza 23→25 | H1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Abruzzo | +0.2 | +0.8 | +0.0 | -0.2 | +0.2 | -3.8 | no |
| Basilicata | -0.3 | -2.7 | +0.0 | -0.2 | +1.2 | -6.1 | no |
| Calabria | -1.0 | -0.4 | +0.0 | -0.1 | +0.4 | -7.7 | no |
| Campania | -0.7 | -1.0 | -0.4 | -0.3 | +2.4 | +0.5 | no |
| Emilia-Romagna | -0.5 | +4.1 | +0.2 | +0.2 | +4.0 | -5.9 | sì |
| Friuli-Venezia Giulia | -0.7 | +7.0 | +0.1 | +0.1 | +1.4 | -9.7 | sì |
| Lazio | -2.9 | +3.0 | -0.1 | -2.1 | +0.7 | -4.4 | sì |
| Liguria | +0.0 | +4.8 | -0.3 | +0.0 | +1.1 | -7.4 | no |
| Lombardia | +0.1 | +7.0 | -0.1 | -1.1 | +1.6 | -11.4 | no |
| Marche | +0.5 | +4.2 | +0.0 | -0.2 | +0.0 | -2.3 | no |
| Molise | -2.4 | +10.7 | +0.0 | +0.1 | +2.0 | -6.4 | sì |
| Piemonte | -0.1 | +6.1 | -0.2 | -0.7 | +1.2 | -5.9 | sì |
| Puglia | -0.5 | -0.7 | +0.0 | -0.2 | +0.6 | -5.0 | no |
| Sardegna | -0.3 | +2.6 | +0.1 | -0.1 | +1.0 | -3.4 | sì |
| Sicilia | -1.4 | -3.4 | -0.1 | -0.5 | -0.3 | -2.1 | no |
| Toscana | -2.2 | +7.3 | -0.2 | +2.0 | +2.1 | -8.5 | sì |
| Trentino Alto Adige | +1.1 | +6.8 | +0.1 | -0.3 | +1.5 | -4.2 | no |
| Umbria | -1.1 | +9.4 | +0.2 | -0.4 | +0.7 | -9.2 | sì |
| Valle d'Aosta | +1.0 | +3.4 | +0.1 | +0.1 | +2.1 | -5.6 | no |
| Veneto | +0.8 | +6.6 | -0.1 | +0.2 | +2.0 | -7.8 | no |


Rapine: media semplice regionale 0,810→0,775 per 1.000 abitanti (Δ=-0,035) nel 2023-25, in aumento in 6 regioni, in calo in 8, invariata in 6. Borseggi: media 3,295→3,110 per 1.000 abitanti (Δ=-0,185), in aumento in 6, in calo in 13, invariata in una. Dal 2019 al 2025 la media delle rapine sale da 0,680 a 0,775, in 13 regioni, scende in 4 ed è invariata in 3. Sono misure distinte, non una misura complessiva della criminalità.

| Coppia di variazioni | Finestra | N | ρ di Spearman | Lettura |
| --- | --- | ---: | ---: | --- |
| Furti vs rischio | 2023-2025 | 20 | -0,001129518 | Associazione monotona quasi nulla nel campione osservato. |
| Rapine vs rischio | 2023-2025 | 20 | 0,136080712 | Descrittiva, esplorativa. |
| Furti vs rapine | 2023-2025 | 20 | 0,132720936 | Descrittiva, esplorativa. |
| Furti vs rischio | 2023-2025, senza Toscana e Campania | 18 | 0,103359187 | Descrittiva, esplorativa. |
| Rapine vs rischio | 2023-2025, senza Toscana e Campania | 18 | 0,126582566 | Descrittiva, esplorativa. |
| Furti vs rapine | 2023-2025, senza Toscana e Campania | 18 | -0,010642689 | Descrittiva, esplorativa. |
| Furti vs rischio | 2019-2025 | 20 | 0,107802495 | Descrittiva, esplorativa. |
| Rapine vs rischio | 2019-2025 | 20 | 0,510114496 | Descrittiva, esplorativa. |
| Furti vs rapine | 2019-2025 | 20 | -0,093683191 | Descrittiva, esplorativa. |
| Furti vs rischio | 2019-2025, senza Toscana e Campania | 18 | 0,148109808 | Descrittiva, esplorativa. |
| Rapine vs rischio | 2019-2025, senza Toscana e Campania | 18 | 0,579710433 | Descrittiva, esplorativa. |
| Furti vs rapine | 2019-2025, senza Toscana e Campania | 18 | 0,095444803 | Descrittiva, esplorativa. |
| Furti vs borseggi | 2023-2025 | 20 | 0,056440188 | Descrittiva, esplorativa. |
| Furti vs degrado | 2023-2025 | 20 | 0,081794201 | Descrittiva, esplorativa. |
| Furti vs sicurezza al buio | 2023-2025 | 20 | 0,121611480 | Descrittiva, esplorativa. |

Leave-one-out esplorativo, ranghi ricalcolati dopo ogni esclusione. Per rapine/rischio 2019-2025, ρ varia da 0,458661 (senza Calabria) a 0,601812 (senza Emilia-Romagna). Per 2023-2025 varia da 0,011699 (senza Umbria) a 0,235790 (senza Toscana). Per furti/rischio 2023-2025 varia da -0,092707 (senza Sicilia) a 0,144552 (senza Molise); nel 2019-2025 da 0,016718 (senza Friuli-Venezia Giulia) a 0,229652 (senza Valle d'Aosta). Non sono intervalli di confidenza e non misurano stabilità inferenziale.


## Controllo serie percettive sovrapposte

`ter-43` e `bes-07SIC022` hanno definizioni pubblicate simili e periodi sovrapposti 2018-2024 per 20 regioni, 140 coppie. I valori differiscono, con scarto assoluto massimo per anno fra 0,233 e 0,515 punti percentuali. Spearman sui 140 valori appaiati è 0,999869, che arrotonda a 1,000. È una relazione osservata fra queste serie, non una prova indipendente né prova che condividano lo stesso processo di rilevazione. Non contarle come conferme indipendenti.

`ims-MULTI_ZONA_CRIMINALITA` ha denominazione “Famiglie che lamentano criminalità nella zona di residenza”, copertura 17, 16, 14, 16, 14, 16, 18, 17 regioni dal 2018 al 2025. Toscana e Campania sono disponibili ma i livelli sono molto diversi dal rischio Bes: per esempio 2025 Toscana 11,2%, Campania 15,5%, contro Bes 27,8% e 38,0%. È una misura distinta, con missingness e formulazione diverse, quindi non prova indipendente né sostituto dell’indicatore BES.

## Fuori estremi, limiti e stato

Esclusione Toscana/Campania lascia 7 divergenze su 18 nel 2023-25 e 9 su 18 nel 2019-25. L’esito non dipende solo dai due casi evidenziati. Non è un test campionario né una prova che la percezione individuale non segua gli eventi: dati regionali aggregati, due misure soggettive campionarie/di popolazione e denominatori diversi.

Limiti: errore campionario e intervalli regionali, composizione demografica, cause e relazione individuale fra esposizione e percezione non sono valutati. Il candidato è stato scelto dopo aver visto risultati sul 2019; confronti aggiunti e leave-one-out sono esplorativi, senza correzione per confronti multipli. Dati aggregati regionali non descrivono le stesse famiglie né consentono spiegazioni individuali. Le medie sono semplici medie regionali, non medie nazionali. Furti e rischio hanno denominatori distinti. Le rapine sono espresse con granularità di un decimale, con sei variazioni nulle nel 2023-2025. Le celle Istat sui reati 2025 sono provvisorie e la serie è ricostruita dal 2019 con la correzione dell'indagine 2022.

La riconciliazione ufficiale riguarda esclusivamente sei indicatori, 20 regioni e tre anni (360 celle), non l'intero CSV né l'incertezza delle stime. Toscana e Campania sono state verificate nelle stesse celle. Codici e anni: furti 07SIC002, rischio 07SIC022, rapine 07SIC004, borseggi 07SIC003, degrado 07SIC021 e sicurezza al buio 07SIC020, 2019, 2023, 2025.
