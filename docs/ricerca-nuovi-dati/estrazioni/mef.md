# MEF, redditi IRPEF su base comunale

> **L'ultimo anno disponibile e' il 2024, non il 2025.** Il Dipartimento delle
> Finanze ha pubblicato i redditi 2024 il **23 aprile 2026**, etichettandoli
> "2025 a.i. 2024" (dichiarazioni 2025 su redditi 2024). Gli ZIP per il 2025 e
> il 2026 restituiscono 404: la serie va dal 2015 al 2024 e la colonna `note`
> del manifesto lo dice in ogni riga.

## Cosa e' stato estratto

Tre indicatori, per 107 province e 20 regioni, per 10 anni: 3.810 righe in
`app/static/data/nuovi/mef.csv`, descritte in `app/static/data/nuovi/mef_manifest.csv`.

| indicator_id | formula | unita' |
|---|---|---|
| `MEF_REDDITO_IMPONIBILE_MEDIO` | `Reddito imponibile - Ammontare in euro` / `Numero contribuenti` | euro per contribuente, 0 decimali |
| `MEF_IMPOSTA_NETTA_MEDIA` | `Imposta netta - Ammontare in euro` / `Numero contributi` | euro per contribuente, 0 decimali |
| `MEF_QUOTA_ALTO_REDDITO` | frequenze delle classi 55.000-75.000, 75.000-120.000, oltre 120.000, sommate e divise per la somma di tutte e 8 le frequenze per classe di reddito complessivo | percentuale di contribuenti, 2 decimali |

## Fonte

- Pagina: <https://www.finanze.gov.it/it/statistiche-fiscali/open-data-comunale-principali-variabili-irpef/>
- ZIP: `https://www1.finanze.gov.it/finanze/analisi_stat/public/v_4_0_0/contenuti/Redditi_e_principali_variabili_IRPEF_su_base_comunale_CSV_{anno}.zip`
- Metodo: <https://www1.finanze.gov.it/finanze/analisi_stat/public/v_4_0_0/contenuti/definizione_variabili_2024_irpef.pdf>
- Sintesi 2024: `sintesi_analisi_dati_2024_irpef_iva.pdf`, stessa directory
- Licenza: **CC BY 3.0 IT**, dal badge "Licenza Creative Commons" della pagina, che rimanda a <http://creativecommons.org/licenses/by/3.0/it/>

Ogni ZIP contiene un solo CSV, UTF-8, separatore `;`. La cache sta in
`lavoro/cache/irpef/` e non e' nel versionamento (`lavoro/` e' escluso da git in
questo repository): il dato che si committa e' il CSV normalizzato.

## Come si aggrega

**Le somme si fanno prima delle divisioni.** Ogni comune versa i suoi numeratori
e denominatori nella provincia e nella regione, e la divisione avviene una volta
sola, sul totale. La media delle medie non e' la stessa operazione: nel test, due
comuni con 9.000 euro e 90 e 10 contribuenti danno 180 euro aggregati e 500 come
media delle medie. Per la quota di redditi alti la differenza e' strutturale,
perche' i pesi sono diversi. Il Trentino Alto Adige e' quindi Bolzano + Trento
sommati, non la media delle due province.

## Il quadro territoriale: la parte delicata

La colonna `Sigla Provincia` cambia dentro la serie, e non solo per le province
che il progetto non ha.

**Le quattro province sarde abolite.** Nel 2015 e nel 2016 la fonte usa `OG`
(Ogliastra), `OT` (Olbia-Tempio), `VS` (Medio Campidano) e `CI`
(Carbonia-Iglesias). Nessuna ha una provincia omonima fra le 107 di
`province_codes.csv`, e non si possono tradurre a mano: i 23 comuni di Ogliastra
non vanno tutti a Nuoro, 22 vanno a Nuoro e Seui va a Sud Sardegna.

La soluzione non e' una tabella scritta a mano: **ogni comune e' attribuito alla
provincia che gli dà l'ultimo anno in cui la fonte lo dichiara**. Dal 2017 il file
non usa piu' quelle quattro sigle, quindi il quadro si legge da li'. Il
risultato e' verificabile e si vede nel conteggio dei comuni:

| provincia | 2015 | 2016 | 2017-2024 |
|---|---|---|---|
| Sud Sardegna | 107 | 107 | 107 |
| Sassari | 92 | 92 | 92 |
| Nuoro | 74 | 74 | 74 |
| Cagliari | 17 | 17 | 17 |
| Oristano | 87 | 87 | 87 |

Senza questo, Sud Sardegna avrebbe avuto 28 comuni nel 2015 e 107 dal 2017, e la
serie avrebbe un salto che non e' un fatto economico. Il quadro e' quello del
2024 applicato a tutti gli anni, che e' l'unico modo che rende confrontabili le
province nella serie.

Se un domani l'ultimo anno di un comune fosse sotto una sigla abolita, la fonte
non direbbe dove e' finito: `attribuzione_comunale` ferma lo script invece di
scegliere. Il caso e' coperto da un test.

**Altri cambi reali, trattati nello stesso modo.** Agugliano fu di Ascoli Piceno
dal 2018 al 2021, Torre de' Busi passò da Lecco a Bergamo nel 2017, 157 comuni in
tutto cambiarono provincia in un anno o nell'altro. Fissare il quadro e' la scelta
giusta anche qui: altrimenti un comune che cambia provincia crea un salto
artificioso nel reddito medio della provincia che perde e in quella che riceve.

**Le regioni.** Il file scrive il Trentino Alto Adige in tre forme diverse nel
corso degli anni (`Trentino Alto Adige`, `Trentino Alto Adige(P.A.Bolzano)`,
`Trentino Alto Adige(P.A.Trento)`) e l'Emilia Romagna senza trattino. Senza
 collasso le stesse regioni diventerebbero serie diverse e i totali nazionali non
tornerebbero; le chiavi si calcolano con `app.profiles.region_key_for`.

**Le righe scartate.** Ogni anno il MEF lascia una riga con
`Codice Istat Comune = 0` e regione `Mancante/errata` o `Non indicato`: non
appartiene a nessun territorio e viene scartata. Restano 7.999 comuni nel 2015 e
7.896 nel 2024.

## Copertura

107 province e 20 regioni in **tutti e dieci gli anni**. Nessun territorio
mancante, nessun territorio inventato.

## Un nome di colonna che ha gia' rotto tutto una volta

La colonna dei contribuenti si chiama `Numero contribuenti`, non `Numero contributi`.
L'errore produceva un `KeyError` che arrivava dopo aver aperto tutti e dieci gli
ZIP e non diceva quale anno si fosse rotto. Ora `COLONNE_NECESSARIE` controlla
tutte le colonne necessarie appena il CSV e aperto, e un test confronta quei
nomi con l'intestazione del file vero.

## Prove

`bin/py -m unittest tests.unit.test_mef_extraction` - 22 prove, tutte verdi.
Coprono intestazioni e decimali, copertura completa, il 2024 come ultimo anno e
la nota che lo dichiara, la licenza e le due URL, l'arrotondamento a meta' per
e su, le medie di medie, il peso della quota, le varianti di nome della regione,
il quadro sardo, l'idempotenza byte per byte e l'uguaglianza fra il conto
nazionale ricalcolato comune per comune e quello ottenuto sommando le province.

`lavoro/verifica_mef.py` fa lo stesso controllo numerico stampandolo, e serve per
il confronto con la fonte a occhio:

```
2015  contribuenti=  40766158  reddito=    19382  imposta=   3806  quota= 4.31
2016  contribuenti=  40866759  reddito=    19514  imposta=   3818  quota= 4.40
2017  contributi=  41205821  reddito=    19502  imposta=   3823  quota= 4.44
2018  contribuenti=  41368109  reddito=    20050  imposta=   3970  quota= 4.70
2019  contribuenti=  41520979  reddito=    20077  imposta=   3977  quota= 4.72
2020  contribuenti=  41177739  reddito=    19797  imposta=   3868  quota= 4.68
2021  contributi=  41494016  reddito=    20746  imposta=   4121  quota= 5.12
2022  contributi=  42022130  reddito=    21752  imposta=   4145  quota= 5.57
2023  contributi=  42564356  reddito=    22745  imposta=   4462  quota= 5.70
2024  contributi=  42832658  reddito=    23658  imposta=   4608  quota= 6.12
```

Il reddito imponibile medio nazionale passa da 19.382 a 23.658 euro e la quota di
contributi sopra i 55.000 euro dal 4,31% al 6,12%: i due andamenti hanno senso
insieme, e la serie e' monotona sul reddito a meno del 2020.

## Come si rilancia

```
bin/py scripts/nuovi_dati/mef.py              # scarica se serve, poi scrive
bin/py scripts/nuovi_dati/mef.py --offline    # legge solo lavoro/cache/irpef
```

Lo script e' idempotente: due esecuzioni producono lo stesso file byte per byte,
e il test lo confronta anche con il file committato.

## Cosa resta fuori, e perche'

- **Il 2025 e il 2026 non esistono.** Non e' un estrazione incompleta: sono gli ZIP
  a non essere pubblicati. Quando usciranno basta allargare `YEARS`.
- **Il tema `Reddito e ricchezza`.** `config/theme_categories.csv` contiene solo
  l'intestazione, quindi la scelta e' mia ed e' discussa nella consegna. Il nome
  esatto arriva da `app/taxonomy.py`.
- **`lavoro/RICERCA_econ.md` non esisteva.** La ricerca e' stata fatta diretta-
  mente sulla fonte e su `lavoro/idx_irpef.html`, l'indice storico delle analisi
  IRPEF pubblicate dal MEF dal 1998.
- **Il quadro territoriale e' del 2024.** Se il progetto volesse anche la serie
  "come era allora", servirebbe un secondo CSV con il quadro di ogni anno; qui
  si e' scelto il quadro confrontabile, che e' quello che serve a una mappa.