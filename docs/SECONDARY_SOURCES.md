# Il registro delle fonti secondarie

Le fonti da cui un articolo indicatore puo' prendere **contesto**, e solo
contesto. Il numero di base viene sempre dalla serie primaria che la pagina gia'
mostra, e la fonte secondaria serve a tre cose: dire che cosa ha detto
l'istituzione quando ha pubblicato quel dato, portare un confronto europeo o
storico che la nostra serie non copre, e reggere un claim comparativo che
altrimenti andrebbe tagliato.

Esiste perche' senza un elenco lo scrittore parte da una ricerca a freddo, e una
ricerca a freddo su un tema statistico italiano restituisce prima gli aggregatori
e i blog che le fonti. Qui ci sono solo istituzioni, e una riga per capire in un
colpo d'occhio se la fonte serve a questo articolo.

**Un URL di questo elenco va comunque aperto prima di citarlo.** Il registro dice
dove guardare, non che cosa c'e' scritto oggi. Una citazione senza URL verificato
si taglia, e una fonte inventata e' l'unico errore da cui non si torna indietro.

## La trappola che passa tutte le guardie

Quasi tutte queste fonti pubblicano **aggregati ponderati**, nazionali o di
ripartizione. Le nostre pagine calcolano la **media semplice dei valori
regionali**. Non sono la stessa grandezza, e nessuna guardia della suite se ne
accorge, perche' l'aritmetica delle due cifre e' corretta separatamente.

Quindi: se citi un dato nazionale, scrivi "dato nazionale <fonte>" e tienilo
staccato dalla "media semplice delle regioni". Non affiancarli come se uno
confermasse l'altro, e non usare la nostra media per dire "in Italia".

## Il registro

Citabilita': **aperta** riuso libero con attribuzione, **report** PDF gratuito
citabile per numero e pagina, **attenzione** parte a pagamento o presso terzi.

| Fonte | Autorevole su | Dove | Citabilita' |
|---|---|---|---|
| Istat, Rapporto BES | benessere, i 12 domini, il territorio | [istat.it, misurazione del benessere](https://www.istat.it/statistiche-per-temi/focus/benessere-e-sostenibilita/la-misurazione-del-benessere-bes/) | aperta |
| Istat, Rapporto Annuale | quadro del Paese, divari, letture di sintesi | [istat.it, rapporto annuale](https://www.istat.it/produzione-editoriale/rapporto-annuale/) | aperta |
| Istat, Rapporto SDGs | Agenda 2030 declinata sul territorio | [istat.it, rapporto SDGs](https://www.istat.it/produzione-editoriale/rapporto-sdgs/) | aperta |
| Istat, Indicatori demografici | natalita', mortalita', migrazioni, invecchiamento | [comunicato, anno 2025](https://www.istat.it/comunicato-stampa/indicatori-demografici-anno-2025/) | aperta |
| Istat, Noi Italia | 100 statistiche tematiche con confronto UE | [noi-italia.istat.it](https://noi-italia.istat.it/) | aperta |
| Eurostat, Regional Yearbook | confronto UE a livello NUTS2 e NUTS3 | [regional yearbook](https://ec.europa.eu/eurostat/web/interactive-publications/regional-yearbook) | aperta |
| Eurostat, Statistics Explained | metodo, definizioni, articoli regionali | [statistics explained](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Main_Page) | aperta |
| SVIMEZ, Rapporto sull'economia del Mezzogiorno | il divario Nord-Sud, con stime proprie | [svimez.it](https://www.svimez.it/) | attenzione, il volume e' a pagamento, i comunicati no |
| Banca d'Italia, Economie regionali | economia regionale, credito, imprese | [economie regionali](https://www.bancaditalia.it/pubblicazioni/economie-regionali/) | report |
| Commissione UE, Cohesion Report | divari regionali nell'Unione | [cohesion report](https://ec.europa.eu/regional_policy/information-sources/cohesion-report_en) | aperta |
| OpenCoesione | politiche di coesione, progetti finanziati | [opencoesione.gov.it](https://opencoesione.gov.it/it/) | aperta (open data) |
| Politiche di coesione, Governo | programmazione, CPT, documenti | [politichecoesione.governo.it](https://politichecoesione.governo.it/it/) | aperta |
| OECD, Regional development | confronto subnazionale internazionale | [oecd.org](https://www.oecd.org/en/topics/policy-issues/regional-development.html) | attenzione, molto e' a pagamento |
| INVALSI | competenze scolastiche per regione | [invalsi.it](https://www.invalsi.it/) | report |
| ISPRA / SNPA | ambiente, consumo di suolo, rifiuti | [isprambiente.gov.it](https://www.isprambiente.gov.it/it), [snpambiente.it](https://www.snpambiente.it/) | report |
| MIMIT | industria, imprese, ricerca e sviluppo | [mimit.gov.it](https://www.mimit.gov.it/it/) | report e dati |
| IFEL (ANCI) | finanza e servizi dei Comuni | [fondazioneifel.it](https://www.fondazioneifel.it/) | report |
| Openpolis | data journalism di controprova | [openpolis.it](https://www.openpolis.it/) | attenzione, e' una fonte secondaria su fonti primarie |

Verificati il 26 luglio 2026, uno per uno, con una richiesta reale.

**Due host rispondono 403 a una richiesta automatica** e non sono per questo
morti: OpenCoesione e OECD bloccano gli user agent non browser. Se WebFetch
torna 403 su quei due, non e' una fonte da scartare, e' un blocco: cerca il
documento specifico invece della home, oppure cita l'istituzione a partire da un
PDF raggiungibile. Non trattare un 403 come "fonte inesistente", perche' il
riflesso giusto altrove ("se non la apro la taglio") qui taglia una fonte buona.

## Come si usa, in pratica

1. Guarda il tema dell'indicatore nel brief e apri **una o due** voci pertinenti.
   Non e' una rassegna stampa, e tre fonti in un pezzo da 600 parole sono troppe.
2. Cerca una cosa sola: qualcosa che il cruscotto non puo' dire. Il commento
   dell'istituto sull'ultimo movimento, la posizione italiana in Europa, un
   caveat di definizione, un controesempio.
3. Verifica l'URL, poi scrivilo in `fonti` come `{testo, url}`, con un `testo`
   che dice che cosa quella fonte sostiene, non solo il suo nome.
4. Se non trovi niente di pertinente, non citare niente. Una fonte messa li' per
   riempire il campo e' peggio del campo vuoto.
