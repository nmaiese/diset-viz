# Gate A: pilota-pensioni
Contratto: v3
Tipo pezzo: scheda indicatore
Esito: FERMO
SHA brief: 28b67c34be8db1ae3f24bc6fd7ca90a5632136b8
Hash brief: 445b074b215814c594bca6b728223e6fc9cbe941aeedcd95d51f85fa1a0c7ad1
Autore/modello: Claude Sonnet (leader del brief, come indicato nella spec)
Giudice/modello: Codex GPT-6 Luna
Domanda: Quanti pensionati hanno un reddito pensionistico basso e dove? La ricerca «pensioni minime» trova corrispondenza solo parziale: questa scheda misura una quota sotto 500 euro lordi, non il trattamento minimo INPS.
Angoli verificati: distribuzione provinciale 2023, da Crotone 16,9% a Bolzano 4,1%; dinamica 2015-2023, calo in tutte le 106 province comparabili ma distanza tra estremi da 13,2 a 12,8 punti
Tesi: Nel 2023 la quota provinciale di pensionati con reddito pensionistico lordo mensile sotto 500 euro varia da 4,1% a Bolzano a 16,9% a Crotone; tra 2015 e 2023 scende in tutte le province comparabili, mentre la distanza tra gli estremi resta ampia. Dato descrittivo, non effetto causale del luogo di residenza.
Codici e confronto: `bes:04BEC006P`, livello provincia, 2015-2023; indicatore oggetto. `bes:04BEC005P` ammesso solo come numero di contesto per Crotone e Milano, non come tesi. Gli indicatori regionali di contesto non servono alla tesi.
Ultimo dato: 2023
Data fonte del dato: 2025-12-04
URL fonte del dato: https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Calabria.pdf
Ruolo indicatori interni: indicatore spiegato e contesto
Fonti esterne verificate:
| istituzione | data fonte | URL aperto | dato o claim | verificata |
|---|---|---|---|---|
| Istat | 2025-12-04 | https://www.istat.it/wp-content/uploads/2025/12/BesT2025_Calabria.pdf | BesT 2025 riporta dato 2023: Crotone 16,9%, Italia 8,9%; testo: «A Crotone (16,9 per cento) l’indicatore è quasi il doppio che in Italia (8,9).» | sì |
| INPS | 2026-03-23 | https://servizi2.inps.it/servizi/osservatoristatistici/api/getAllegato/?idAllegato=1037 | Osservatorio su pensioni vigenti all’1.1.2026; specifica che basse classi di importo non misurano direttamente la condizione economica dei pensionati perché possono ricevere più prestazioni o altri redditi. Dato INPS: pensioni, soglia 750 euro, non indicatore Bes 2023 sotto 500 euro. | sì |
Grafico con dati esterni: non richiesto per scheda indicatore
| criterio | esito | prova verificabile | limite |
|---|---|---|---|
| Indicatore oggetto, domanda e tesi sono coerenti con una scheda | sì | `brief.md` identifica `bes:04BEC006P`, tasso provinciale sotto 500 euro lordi mensili, 2023; Istat BesT Calabria conferma Crotone 16,9% e anno 2023. Il CSV del repository conferma Crotone 16,9 e Bolzano 4,1. | La formula «dove vivi cambia di quattro volte la probabilità» va resa descrittiva: il dato osserva quote territoriali e non dimostra un effetto causale della residenza. |
| Prove esterne datate e dato più recente | sì | Report Istat BesT 2025, data 2025-12-04, contiene dato 2023 e citazione letterale riportata sopra. La fonte INPS, documento del 2026-03-23, è usata solo per limiti, con anno di osservazione 1.1.2026. | INPS non verifica il dato Bes: usa unità pensioni e soglia 750 euro; non va presentato come dato sotto 500 euro né come serie provinciale. |
| Limiti, definizioni e cause sono gestiti | no | Il brief vieta di chiamare 500 euro «pensione minima» o soglia di povertà, distingue reddito pensionistico da reddito personale/familiare, non attribuisce cause e tratta Bolzano 6,9→4,1 come anomalia non spiegata. Ma la query «pensioni minime» è detta solo «corrispondenza parziale» nella sezione 9 e il lead proposto non la chiarisce. | La spec richiede che il lead dica subito che la scheda non tratta la pensione minima INPS. Inoltre il luogo di residenza o erogazione non è chiarito dalla fonte, limite segnalato in `fonti.md` ma assente dalla struttura proposta. |
| Livello e metadati richiesti | sì | Prima riga di `brief.md`: `level: provincia`. Il brief richiede anche `key: "bes:04BEC006P"`, `vintage: 2023`, fonti 1, 2 e 4 e titoli SEO. | Sono requisiti per il front matter della futura scheda, non metadati già presenti in un front matter completo. |
| Brief scrivibile senza affermazioni non sostenute | no | Ho ricalcolato dal CSV: Crotone 16,9%, Bolzano 4,1%, media semplice 8,8561%, distanza 12,8 punti nel 2023 e 13,2 nel 2015; calo in tutte le 106 province comparabili. Napoli 18,9→15,6; Milano 7,4→6,0; Bolzano 8,6→4,1. | I numeri centrali tornano. Il lead deve chiarire la ricerca parzialmente corrispondente e sostituire la formulazione di probabilità con una quota osservata; aggiungere il limite territoriale non documentato prima della scrittura. |
Motivo: Le cifre richieste sono riproducibili dai dati del repository e le fonti supportano definizione, anno, valore di Crotone e caveat INPS. Il brief non passa perché il lead prescritto non avvisa subito chi cerca «pensioni minime» che l’indicatore non misura la prestazione minima INPS; inoltre «cambia la probabilità» può far leggere un’associazione descrittiva come effetto della residenza. Il limite sul significato territoriale del dato è presente nelle fonti raccolte ma non entra nella struttura proposta.
Correzione: Minima. Nel lead dichiarare che la corrispondenza con «pensioni minime» è parziale e che il dato riguarda la quota sotto 500 euro, non il trattamento minimo INPS. Riscrivere la tesi come confronto descrittivo di quote territoriali, senza causalità. Inserire nei limiti che la fonte non chiarisce se la provincia indica residenza o luogo di erogazione. Poi ricalcolare hash e SHA del brief e riaprire Gate A sul brief aggiornato.
Destinatario: leader del brief
Data: 2026-10-08
