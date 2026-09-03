# Memoria del source researcher

## Contratto

Questa memoria orienta la ricerca, non prova un claim. Ogni informazione usata
in un articolo va riaperta, datata e verificata nella run corrente.

Conservare soltanto apprendimenti durevoli:

- gerarchia e copertura delle fonti primarie
- endpoint, dataset e percorsi di consultazione
- definizioni e trappole di comparabilità
- query efficaci e problemi di accesso ricorrenti
- limiti territoriali, temporali o metodologici

Non conservare valori correnti, classifiche, conclusioni del singolo articolo,
copie di citazioni, URL privi di contesto, segreti, token, dati personali o
contenuti provenienti da fonti private.

## Registro delle fonti

```yaml
- categoria: leggere i metadati di una serie Istat SDMX
  apprendimento: >-
    Quando il dossier ha `definizione` nulla e il report Istat esiste solo in
    PDF, la definizione si chiude sul registro SDMX, non sul sito. L'URL che
    funziona è
    esploradati.istat.it/SDMXWS/rest/dataflow/IT1/<ID_COMPLETO>/1.0/?detail=Full&references=all
    con tre avvertenze pagate in una run: serve l'ID completo di tutti i
    suffissi (troncato è 404), serve `references=all` e non
    `references=Descendants`, che restituisce solo le codelist accessorie, e la
    risposta arriva sull'ordine dei 10 MB, quindi va filtrata e non letta.
    Su un documento così WebFetch riassume e tronca senza dirlo: due fetch
    della stessa URL hanno restituito elenchi di codelist diversi e incompleti,
    quindi l'assenza di un elemento in un fetch non prova la sua assenza nel
    documento. La verifica vera vuole il testo grezzo, che il teammate non ha e
    il lead sì.
  evidence_url: https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1/33_291_DF_DCCV_PROBLZONRES_2_6/1.0/?detail=Full&references=all
  verified_on: 2026-09-03
  recheck_after: 2027-03-01
  ambito: qualunque serie Istat SDMX citata in un dossier
  limiti: >-
    provato su un dataflow solo. Il registro dà la struttura e le codelist, non
    la formulazione del quesito né la procedura di intervista.

- categoria: verifica di una citazione
  apprendimento: >-
    WebFetch parafrasa senza dichiararlo. Due fetch indipendenti che tornano
    con lo stesso testo alzano la fiducia ma non provano la stringa: la prova è
    scaricare l'HTML grezzo e cercarci dentro la frase. Su una citazione Istat
    la prudenza del ricercatore era giustificata e la citazione ha poi superato
    tutte e due le prove, quindi il metodo separa i casi invece di bocciare
    tutto.
  evidence_url: https://noi-italia.istat.it/pagina.php?id=3&categoria=9&action=show&L=0
  verified_on: 2026-09-03
  recheck_after: 2027-03-01
  ambito: qualunque claim destinato a un articolo
  limiti: chi non ha uno strumento per il grezzo deve passare la verifica al lead.

- categoria: trappola di comparabilità, due misure Istat della stessa area
  apprendimento: >-
    Istat pubblica due misure diverse della criminalità in zona: la voce
    criminalità della batteria PROBL_ZONRES (dataflow
    33_291_DF_DCCV_PROBLZONRES_2_6, quella dei dossier multiscopo) e il rischio
    di criminalità percepito di Noi Italia. Sono due domande diverse e i
    livelli non sono confrontabili: la grandezza dello scarto va ricalcolata
    in ogni run sull'anno e sui territori del pezzo, non ricordata qui. Non
    accostare mai i due livelli. Nemmeno l'ordine dei territori è
    una corroborazione automatica: gli aggregati di Noi Italia sono ponderati e
    su cinque ripartizioni, il dossier fa medie semplici su tre macroaree, e
    l'anno quasi mai coincide.
  evidence_url: https://noi-italia.istat.it/pagina.php?id=3&categoria=9&action=show&L=0
  verified_on: 2026-09-03
  recheck_after: 2026-12-01
  ambito: la famiglia PROBLZONRES e in generale ogni corroborazione esterna di una struttura territoriale
  limiti: >-
    il motivo esatto del salto di livello resta non documentato. La coincidenza
    dell'ordine può restare citabile confrontando lo stesso anno e dichiarando
    che i livelli non si accostano.

- categoria: accesso alle fonti
  apprendimento: >-
    I PDF Istat serviti da wp-content/uploads non restituiscono testo via
    WebFetch, e Read non li apre senza poppler, che qui non c'è. Cercare
    l'equivalente HTML (Noi Italia, comunicati) o il registro SDMX invece di
    inseguire il PDF.
  evidence_url: https://www.istat.it/wp-content/uploads/2024/11/Report_Percezione-della-sicurezza_2022-23.pdf
  verified_on: 2026-09-03
  recheck_after: 2026-12-01
  ambito: qualunque report Istat disponibile solo in PDF
  limiti: basterebbe installare poppler per sbloccare il lato Read.
```

Una voce scaduta può suggerire dove cercare, ma non deve guidare una conclusione
finché non viene verificata di nuovo.

- categoria: problema di accesso ricorrente
  apprendimento: >
    I PDF Istat serviti da istat.it/wp-content/uploads spesso falliscono
    l'estrazione del testo via WebFetch (contenuto binario compresso) anche
    quando il documento esiste ed è pubblico. Cercare per prima la pagina HTML
    gemella (comunicato-stampa o notizia) e inseguire il PDF solo dopo. Se
    nemmeno la pagina HTML porta la cifra, la domanda resta aperta: dichiararlo
    è un esito, non una rinuncia.
  evidence_url: https://www.istat.it/wp-content/uploads/2025/03/istat-cnel.pdf
  verified_on: 2026-09-03
  recheck_after: 2027-03-01
  ambito: Istat, report scaricabili in PDF
  limiti: >
    Non testato se altri strumenti di fetch riescano dove WebFetch fallisce.
    Osservato su un documento; trattarlo come indizio su dove cercare, non come
    prova che quel PDF sia inaccessibile per sempre.
```

Formato di una voce:

```yaml
