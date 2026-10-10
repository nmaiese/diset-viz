# Gate A indipendente: furti e sicurezza percepita

Esito: FERMO

Data: 7 ottobre 2026, Europe/Rome. Destinatario: leader Claude Sonnet 5.5 e coordinatore della PR draft #358. Autore del brief: Claude Sonnet 5.5. Giudice: Codex GPT-6 Astra, `codex-gpt-6-astra`, contesto nuovo, famiglia diversa, un solo giro.
SHA esaminato: `26053d28a57521b202a927ed83440fbf027f41cc`. SHA-256 di `brief.md`: `3830854bc1d060e51f66861ab1588ec3e71f1cdd959fc1e17055f6789da9dde8`. SHA-256 del CSV: `2104328cc934146159e6e036cc0205e839f3a86bc6ca47a00bbffbb4784e36a6`. I riferimenti di riga sotto appartengono a questo SHA.

Domanda esaminata: "Se nella mia regione diminuiscono i furti, perché non mi sento più sicuro?" (`brief.md:13`). Tesi esaminata: la variazione dei furti "non dice" quella del rischio, mentre le rapine lo accompagnano meglio nella finestra lunga (`brief.md:21`). Una risposta sul perché personale non è identificabile. Una risposta utile, descrittiva e territoriale esiste: un calo dei furti domestici non implica che tutte le misure della sicurezza migliorino insieme.
Codici e confronto: `bes-07SIC002` furti, `bes-07SIC022` rischio, `bes-07SIC004` rapine. Variazioni assolute regionali 2023-2025 e 2019-2025, N=20, poi N=18 escludendo Toscana e Campania. Contesto contrario: `bes-07SIC003`, `bes-07SIC021`, `bes-07SIC020`. Il censimento contiene 31 riferimenti, di cui 6 provinciali e uno di tema adiacente. `ter-43` e la serie IMS non vengono contati come repliche.

| criterio | sì/no | prova | limite |
| --- | --- | --- | --- |
| 1. Corregge la sola classifica e risponde alla domanda | no | `brief.md:17,21,30,61`: contrappone livelli e variazioni, ma chiama un coefficiente prossimo a zero "prova del distacco" e promette "non dice quanto cambia". La domanda personale e causale resta senza risposta, come ammette `brief.md:95`. | La distinzione fra livelli e cambiamenti è utile. N=20, selezione guidata dai risultati e assenza di associazione monotona marcata non provano indipendenza, assenza di altri legami o capacità predittiva nulla. Occorre restringere domanda e tesi insieme. |
| 2. Tre misure pertinenti realmente incrociate | sì | `brief.md:37-57,76-90` confronta tutte e tre le coppie, due finestre e gli stessi territori. Rapine/rischio cambia con la finestra anche dopo il ricalcolo corretto: 0,136 nel periodo breve, 0,510 nel lungo. | Le rapine non sono ornamento se servono a mostrare che il risultato cambia secondo reato e finestra. Sono un esito esplorativo, non la spiegazione del rischio. Famiglie e abitanti consentono un confronto ecologico delle stesse regioni, non un confronto fra le stesse persone o una somma dei tassi. |
| 3. Formule, osservazioni, N ed esclusioni verificabili | no | `numeri.md:9-15,25-73,81-102` fornisce chiavi e formula corretta, ma i coefficienti in `numeri.md:21,23,50,109-113` e `brief.md:53-85` non rispettano gli ex aequo dei decimali pubblicati. Due ricalcoli indipendenti, descritti sotto, localizzano l'errore. | I conteggi 8/20 e 11/20 sono corretti. Il blocco riguarda numeri derivati, non celle inventate: 360/360 celle riconciliate con Istat. Formula scritta correttamente non basta se l'esecuzione ordina rumore binario. |
| 4. Distingue risultato e causa | sì | `brief.md:23,93-95,108-110` dichiara meccanismo ignoto, vieta cause su media/social/composizione e inferenze individuali. | L'ignoto non boccia il pezzo. Va però rispettato anche nella domanda e nell'apertura. "Variazioni non distinguibili dal rumore" è troppo categorico senza intervalli: si deve dire che la loro precisione non è stata valutata. |
| 5. Controllo contrario fissato prima e risultati negativi conservati | sì | `secondo-pezzo-scelta.md:41-42` prescrive finestra 2019-2025 ed esclusione Toscana/Campania prima del lavoro dello scout. `brief.md:74-90` applica entrambi e conserva H2 negativa. Ricalcolo: 7/18 e 9/18 divergenti, con coefficienti corretti sotto. | Si conferma solo la persistenza descrittiva dei casi e di una debole associazione monotona furti/rischio. Il sondaggio aveva già visto risultati sul 2019 (`secondo-pezzo-scelta.md:22`): non è preregistrazione confermativa su dati ignoti. Attese, nuove coppie e leave-one-out sono esplorativi. |

Motivo del fermo: **numeri e formulazione della tesi, non sola forma del brief**. La lettura descrittiva resta possibile, ma non si consegnano allo scrittore coefficienti errati e un "minimo 2023" non qualificato. Un no ferma lo scrittore. Non applicare l'eccezione per un ritorno aggiuntivo riservata ai soli difetti di forma. Nessun secondo giro Astra automatico.

## Ricalcolo indipendente e difetto degli ex aequo

Ho letto direttamente `app/static/data/Assoluti_BES_Regione.csv`, separatore `;`, selezionando `Area=Regione` e `Livello/Variazione=Livello`. Chiave univoca `(idIndicatore,Territorio,Anno)`, nessun duplicato o mancante nelle 360 celle dei sei indicatori e tre anni. Trentino Alto Adige conta una volta, Bolzano e Trento non entrano. Nessun valore importato dai calcoli dello scout o del leader.
Formula: ΔX(r)=X(r,2025)-X(r,anno iniziale), in unità originali. Divergente se Δfurti<0 e Δrischio>0, zeri esclusi. Rango medio R(x)=numero di valori strettamente minori di x +(numero di valori uguali a x +1)/2. ρ=Σ(Rx-m)(Ry-m)/√[Σ(Rx-m)²Σ(Ry-m)²], con m=(N+1)/2. Dopo un'esclusione si ricalcolano i ranghi. Nessuna ponderazione, inferenza o p-value.
Prima implementazione: parsing `Decimal` prima della sottrazione, ranghi da conteggi, `statistics.correlation`. Seconda: valori convertiti in decimi interi, ranghi da ordinamento e raggruppamento, formula esplicita sopra. Le due restituiscono gli stessi coefficienti. Ripetendo con sottrazioni `float` si riproducono esattamente i valori del brief, compreso 0,4693911072774274: diagnosi verificata, non ipotesi.

| Finestra e campione | N | Divergenti | ρ furti/rischio corretto | ρ rapine/rischio corretto | ρ furti/rapine corretto |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023-2025, tutte | 20 | 8 | -0,001129518 | 0,136080712 | 0,132720936 |
| 2023-2025, senza Toscana/Campania | 18 | 7 | 0,103359187 | 0,126582566 | -0,010642689 |
| 2019-2025, tutte | 20 | 11 | 0,107802495 | 0,510114496 | -0,093683191 |
| 2019-2025, senza Toscana/Campania | 18 | 9 | 0,148109808 | 0,579710433 | 0,095444803 |

Ex aequo, N=20, notazione valore:molteplicità. Nel 2023-2025 furti {-0,7:2, -0,5:2, -0,3:2}, rischio {7,0:2}, rapine {-0,2:2, -0,1:4, 0:6, 0,1:4, 0,2:2}. Nel 2019-2025 furti {-3,3:3}, rischio {1,3:2, 2,6:2, 6,4:2}, rapine {-0,1:2, 0:3, 0,1:4, 0,2:4, 0,3:2, 0,4:3}. Per esempio le rapine +0,4 di Emilia-Romagna, Friuli-Venezia Giulia e Toscana devono avere rango 19. Le sottrazioni binarie 1,2-0,8 e 0,9-0,5 producono invece 0,3999999999999999 e 0,4 e spezzano il pari merito.
Anche il leave-one-out del brief va ricalcolato: rapine/rischio 2019-2025 da 0,458661 senza Calabria a 0,601812 senza Emilia-Romagna. Nel 2023-2025 da 0,011699 senza Umbria a 0,235790 senza Toscana. Non sono intervalli di confidenza. La granularità a 0,1 e la dipendenza dalla finestra restano limiti reali dopo la correzione informatica.
Localizzazione CSV: per Toscana, furti 2019/2023/2025 alle righe 19080/19084/19086, rischio 21244/21248/21250, rapine 19960/19964/19966. Per Campania, furti 18816/18820/18822, rischio 20992/20996/20998, rapine 19696/19700/19702. Le altre osservazioni sono riproducibili con le chiavi dichiarate e l'insieme delle venti regioni del CSV.

## Cosa resta vero e cosa correggere

Confermati gli otto casi 2023-2025 elencati in `numeri.md:19` e gli undici 2019-2025 in `numeri.md:50`. Le attese con margini fissi sono 13×15/20=9,75 e 17×13/20=11,05. I conteggi osservati non le superano. Il brief riconosce questo fatto (`brief.md:29`), ma sposta impropriamente la "prova" sui coefficienti quasi nulli nella riga successiva. Né conteggi né ρ dimostrano indipendenza.
Confermate le medie semplici regionali: furti 9,380 / 7,380 / 6,860, rischio 22,095 / 18,830 / 22,610, rapine 0,680 / 0,810 / 0,775, nell'ordine 2019/2023/2025. Il calo medio dei furti dal 2019 è 26,8657%. Non è un calo "ovunque" (`brief.md:61`): 17 regioni scendono, Veneto e Valle d'Aosta salgono, Friuli-Venezia Giulia resta uguale. Arrotondando convenzionalmente a due decimali, 22,095 diventa 22,10, non 22,09.
Il 2023 è il minimo **solo dei tre anni selezionati**, non della serie né un minimo locale. Media del rischio nelle venti regioni: 2019 22,095%, 2020 18,405%, 2021 16,640%, 2022 18,025%, 2023 18,830%, 2024 21,505%, 2025 22,610%. Il minimo dell'intera serie disponibile 2005-2025 è 2021. Correggere `brief.md:31,112` e l'assunzione ripetuta nella spec. È lecito parlare di risalita già iniziata prima del 2023 e di vicinanza al 2019 nel 2025, senza attribuirne la causa.
H2 negativa conservata e ricontrollata: nel 2023-2025 degrado in aumento in 8/8 divergenti e 10/12 altre, sicurezza al buio in calo in 8/8 e 11/12. Rapine in aumento in 4/8 e 2/12 nel breve, 8/11 e 5/9 nel lungo. Questo non identifica una spiegazione specifica delle regioni divergenti e non dimostra equivalenza statistica fra gruppi. La Campania diverge anch'essa dal 2019, quindi il contrasto direzionale con Toscana vale soltanto nel 2023-2025.

## Fonti, popolazioni e riconciliazione ufficiale

Verificato il [capitolo Sicurezza, Rapporto BES 2024, pagina 139](https://www.istat.it/wp-content/uploads/2025/11/07-Sicurezza-1.pdf#page=15): furti per 1.000 famiglie, rapine per 1.000 abitanti, rischio sul totale delle famiglie. Furti e rapine correggono le denunce con l'indagine di vittimizzazione, il rischio viene da Aspetti della vita quotidiana. Sicurezza al buio e degrado riguardano persone di almeno 14 anni. Non sono tre campioni individuali appaiati. La compatibilità è territoriale, sufficiente solo per il confronto ecologico esplicitato.
La mancata riconciliazione dichiarata in `brief.md:111` era un limite reale degli input, ma è stata risolta in questo giro. Il browser non legge ZIP, mentre il download HTTP con `urllib.request` e lettura in memoria con `zipfile` e `openpyxl` riescono. Dalla [pagina ufficiale degli indicatori BES](https://www.istat.it/statistiche-per-temi/focus/benessere-e-sostenibilita/la-misurazione-del-benessere-bes/gli-indicatori-del-bes/) ho seguito l'aggiornamento intermedio 2026 verso [APPENDICE-STATISTICA-2.zip](https://www.istat.it/wp-content/uploads/2026/05/APPENDICE-STATISTICA-2.zip). Nessun archivio scritto nel worktree.
Prova: ZIP di 1.789.151 byte, SHA-256 `9003db40394edeb2c88bfa6b6fb56a176c6c00f7e24897b4f5d9af5db40cbebc`. Membro `APPENDICE STATISTICA 2/indicatori_regione_sesso.xlsx`, SHA-256 `17854ca626dd6b4e24e4d5a76927ca57df99a257e4b3cffb290b61e455070cba`, foglio `Foglio1`, selezione `SESSO=Totale`. Confronto esatto Decimal su sei codici × venti regioni × tre anni: **360/360 coincidenti, zero mancanti**. Uniche normalizzazioni dei nomi necessarie: Valle d'Aosta/Vallée d'Aoste e Trentino-Alto Adige/Südtirol verso i nomi del CSV. Toscana: righe XLSX furti 5343, rapine 5403, rischio 5767. Campania: 5349, 5409, 5773. Colonne 2019/2023/2025 identificate dall'intestazione.
Limiti nuovi da riportare dal campo `NOTA` dell'XLSX: furti, borseggi e rapine 2025 sono provvisori. La serie è ricostruita dal 2019 usando la correzione dell'indagine Sicurezza dei cittadini 2022. Per borseggi e rapine la tavola regionale totale non equivale al totale della tavola per età, limitata alle persone di almeno 14 anni. La riconciliazione copre le 360 celle dichiarate, non l'intero CSV né l'incertezza delle stime.

## Ritorno mirato al leader

Correzione richiesta: aggiornare tutti i coefficienti e i leave-one-out con ranghi che rispettino gli ex aequo, correggere il minimo e "ovunque", sostituire la "prova del distacco" con la descrizione circoscritta, riformulare la domanda senza promettere una causa individuale. Integrare la prova delle 360 celle e i limiti ufficiali su provvisorietà e ricostruzione. Le modifiche a brief/numeri/fonti/dossier spettano ai rispettivi proprietari, non sono state eseguite da questo giudice.
Formulazione massima consentita per la revisione del brief: "Nelle venti regioni, il calo dei furti in casa non coincide sempre con un calo del rischio percepito. I cambiamenti dei furti e del rischio mostrano una debole associazione fra i ranghi nelle due finestre considerate. Per le rapine l'associazione è maggiore dal 2019 al 2025 e molto più debole dal 2023 al 2025. Questi confronti regionali non spiegano perché una persona si senta insicura." Domanda compatibile: "Meno furti in casa significa sempre meno rischio percepito nella regione?" Questa formulazione non autorizza lo scrittore prima della chiusura del gate.
Limiti obbligatori anche per quella formulazione: analisi esplorativa scelta sui risultati, N=20 o N=18 dichiarato, nessuna prova di indipendenza o causalità, denominatori distinti, medie regionali non nazionali, rapine a un decimale e sensibili alla finestra, H2 negativa visibile, reati 2025 provvisori. Mancano valutazione dell'errore campionario, meccanismi causali, verifica aggiornata della domanda Search Console e prova HTML, non richieste per produrre questo verdetto.

## Verifica e stato Git

Stato iniziale: ramo `divario/furti-sicurezza-percepita`, HEAD indicato sopra, `git status --short` vuoto. Unico file posseduto e prodotto: questo rapporto. Il CSV estraneo `data/derived/casa_titolo_godimento.csv` non è stato toccato. Calcoli eseguiti con `bin/py` e interprete selezionato tramite `DIVARIO_PYTHON`. Nessun push, merge, messaggio GitHub, altro worker o bozza.
Verifiche completate: ricalcolo in Decimal e in decimi interi, riproduzione del difetto con float, riconciliazione ufficiale 360/360, esecuzione del frammento sotto, controllo dei cinque criteri e dell'hash del brief, `git diff --cached --check -- lavoro/furti-sicurezza-percepita/gate-a.md` senza errori. Stato prima del commit: soltanto questo file aggiunto all'indice, nessuna modifica fuori indice.
Limite test: suite completa `bin/py -m unittest discover -s tests -v` avviata per la regola generale del router, poi interrotta su istruzione diretta perché facoltativa per questa spec. Inviato SIGINT soltanto al processo avviato da questo worker, PID 492196, uscita verificata 130. Nessun esito verde della suite completa dichiarato. Il Gate A resta FERMO per i rilievi numerici e semantici, indipendentemente dalla suite.
Riproduzione minima dei coefficienti e dei conteggi, dalla radice del worktree con interprete configurato:
```sh
bin/py - <<'PY'
import csv, statistics
from decimal import Decimal
with open('app/static/data/Assoluti_BES_Regione.csv') as f:
    d = {(r['idIndicatore'], r['Territorio'], int(r['Anno'])): Decimal(r['Dato'].replace(',', '.')) for r in csv.DictReader(f, delimiter=';') if r['Area'] == 'Regione' and r['Livello/Variazione'] == 'Livello' and r['idIndicatore'] in ('07SIC002', '07SIC022', '07SIC004')}
def rank(v):
    return [sum(a < x for a in v) + (sum(a == x for a in v) + 1) / 2 for x in v]
for year in (2023, 2019):
    for excluded in ((), ('Toscana', 'Campania')):
        regions = sorted({r for c, r, y in d if y == 2025 and r not in excluded})
        x, p, z = ([d[c, r, 2025] - d[c, r, year] for r in regions] for c in ('07SIC002', '07SIC022', '07SIC004'))
        print(year, excluded, len(regions), sum(a < 0 and b > 0 for a, b in zip(x, p)), [statistics.correlation(rank(a), rank(b)) for a, b in ((x, p), (z, p), (x, z))])
PY
```
