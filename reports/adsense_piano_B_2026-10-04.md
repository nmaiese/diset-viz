# Piano B AdSense: che cosa fare di ogni tipo di pagina

Autore: C-DIV, 4 ottobre 2026. Base: audit A parziale (`reports/adsense_audit_2026-10-03.md`, commit d85f4fb7, 618 URL misurate). Il resto dell'audit A (URL Inspection a campione, CMP, Core Web Vitals, link rotti) va al worker deepseek di C1 e puo cambiare l'ordine qui sotto. Niente di questo e implementato: ogni ondata ha la sua spec in `/mnt/c/Users/Nilo/orca/specs/divarioitalia/`.

## Che cosa dicono i numeri, in una riga
Il rifiuto e "contenuti di scarso valore". Google non ci ignora: indicizza la maggior parte delle schede (287 su 410) e delle province (100 su 107). Ci vede, e non ci trova abbastanza di nostro: province e regioni sono quasi cloni l'una dell'altra, 338 schede su 410 condividono piu di meta del testo con un'altra, e 10 delle 12 pagine di "qualita della vita" sono la stessa classifica con le righe in altro ordine, ognuna con il proprio canonical e nella sitemap. Il lavoro e togliere il duplicato e dare testo proprio dove il traffico c'e gia, non pubblicare di piu.

## Decisione per tipo di pagina
| Tipo (URL in sitemap) | Decisione | Perche, in numeri | Impatto atteso | Rischio |
|---|---|---|---|---|
| qualita-della-vita, varianti `?profilo=` (10) | **Consolidare**: canonical sulla classifica base, `noindex, follow`, fuori sitemap. I link restano. | Stessa tabella, righe riordinate; unico mediano 161 parole, 10 su 12 quasi cloni all'80%. Sono le piu deboli di tutto il sito. | Sitemap 618 a 608. Toglie il peggior blocco dal giudizio. Clic persi: ~0 (15 clic in totale sul tipo, quasi tutti sulle basi). | Basso. Si torna indietro rimettendo il canonical. |
| qualita-della-vita, base regioni/province/hub (3) | **Arricchire**: un testo proprio per classifica (che cosa misura il punteggio, chi e in testa e perche, quanto pesa ogni profilo, limiti), tutto ricavato dai dati. | Tre pagine sono il cuore del brand "divario". Oggi hanno la tabella e poco altro. | Portarle sopra 500 parole uniche. | Basso. |
| quiz, 5 pagine di gioco | **Escludere**: `noindex`, fuori sitemap, e **nessun annuncio** su queste pagine (verificare dove carica AdSense). | 117-495 parole, interfaccia e non contenuto: sono schermate senza testo editoriale, il caso tipico che AdSense non vuole con annunci. Valgono 2 clic in 28 giorni. | Sitemap 608 a 603. Elimina il segnale piu esplicito di "poco valore". | Basso: si perdono ~2 clic al mese. Il gioco resta, serve agli utenti non a Google. |
| quiz hub `/quiz` | **Escludere** insieme alle pagine di gioco finche non ha 300 parole proprie. | 117 parole. Un testo di presentazione si scrive dopo, non e prioritario. | Sitemap 603 a 602. | Basso. |
| province (107) | **Arricchire**, poi misurare. Se dopo l'ondata la somiglianza mediana resta sopra 0,5: `noindex` sul 50% con meno impressioni. | 100% quasi duplicate fra loro, unico mediano 506 parole, ma 100 su 107 sono indicizzate e 842 impressioni: Google le tiene, non le premia (3 clic). Toglierle tutte butta un asset; lasciarle cosi e il difetto. | Piu costoso: 107 pagine. Obiettivo misurabile: Jaccard mediano sotto 0,5. | Medio: arricchire con frasi generate in serie e un altro scalato. Vincolo: ogni modulo nuovo deve dire un fatto che cambia da provincia a provincia (scarto dalla sua regione, vicine, variazione 5 anni, indicatore che stacca), mai riempitivo. |
| regioni (20) | **Arricchire** con gli stessi moduli delle province, piu 20 aperture scritte a mano a cura del titolare solo dove vuole. | Quasi duplicate al 100% ma con 1180 parole uniche, il tipo piu ricco. Impressioni: 35. | Basso costo, la base e buona. | Basso. |
| indicatore (410) | **Dividere in tre per dato e non a occhio**: (a) scheda con prosa scritta e impressioni: tenere e rifinire; (b) scheda senza prosa scritta e senza impressioni in 28 giorni: `noindex` + fuori sitemap finche non ha un testo; (c) le 30 con piu impressioni: priorita di arricchimento. Prima misurare quante sono (a), (b), (c). | 383 file in `content/indicators` contro 410 URL: ~27 mancano; 338 schede condividono oltre meta del testo con un'altra, ma e boilerplate di sezioni fisse piu tabelle. Il rischio e in (b). | Fino a ~100 URL fuori sitemap se (b) e grande; sitemap piu corta e solo schede con voce propria. Non toccare le 287 con impressioni senza guardare. | Medio: togliere schede che Google gia mostra perde clic. Per questo (b) si decide con le impressioni, mai a ipotesi. |
| indicatore/province (22) | **Tenere**, rivedere dopo l'ondata schede. | Unico mediano 529, nessun clone ≥80%. | Nessuno. | Basso. |
| tema (12), blog (17), home, metodologia, chi-siamo, privacy, contatti, termini | **Tenere**. `contatti` (284) e `termini` (324) sopra 250 ma sono pagine legali: nessun intervento. | Sopra soglia, nessun duplicato. | Nessuno. | Nessuno. |
| blog | **Aumentare**: da 17 a 30 articoli veri (spec). | Il blog e la parte che regge meglio: 924 parole uniche mediane, 29 clic da 13 pagine. | +13 articoli. Non e un'ondata di worker: ogni articolo passa dal titolare ("niente online da solo", pipeline non attiva), quindi serve un ritmo concordato (proposta: 3 a settimana in bozza). | Alto sui tempi, non sul rischio. |

## Ordine, a ondate (ognuna su un suo ramo, review di un agente diverso, red team a contesto pulito prima di produzione, merge solo da Cowork)
0. **Identita** (fatta, ramo `agenti/identita-editoriale`): resta il blocco su `intestatario_legale` in /privacy.
1. **Ondata 1: togliere il peggio** (qualita-della-vita varianti, quiz, annunci sui quiz). Spec `SPEC-adsense-ondata-1-consolidare.md`. Poche righe di codice, effetto subito sulla sitemap. Costo: 1 worker, mezza giornata.
2. **Ondata 2: misura e schede** (porta lo script dell'audit in `scripts/`, classifica le 410 schede in (a)(b)(c), applica (b)). Spec `SPEC-adsense-ondata-2-schede.md`. Costo: 1 worker, 1 giornata. Qui si ripete anche l'audit: e il criterio di uscita della spec.
3. **Ondata 3: province e regioni** (moduli con fatti propri, poi misura). Spec `SPEC-adsense-ondata-3-province-regioni.md`. E la piu costosa e la piu rischiosa per qualita: un worker, review umana a campione di 10 pagine prima del merge.
4. **Ondata 4: blog a 30** e le due pagine di qualita arricchite: cadenza e approvazione del titolare, non spec di worker.

Perche questo ordine: 1 e 2 riducono, costano poco e sono reversibili; 3 aggiunge testo e si fa solo dopo aver visto che cosa resta debole dopo 1 e 2. Non fare ancora: scrivere testo nuovo sulle schede di tipo (b), togliere province o regioni dall'indice, ripresentare la richiesta ad AdSense (solo dopo l'audit ripetuto che passa i criteri e due settimane di copertura in crescita).

## Criteri di uscita (da ripetere con lo script)
La spec chiede 90% delle URL con 300 parole uniche: oggi la soglia e passata quasi ovunque e non basta, quindi aggiungo due criteri: nessun tipo con somiglianza mediana fra pagine sopra 0,5 se ha piu di 10 pagine, e nessuna pagina con meno di 300 parole uniche in sitemap. Il criterio sul testo unico si misura con lo stesso script dell'audit A (limiti dichiarati nel report).

## Che cosa non so ancora
- Se Google ha escluso pagine che oggi risultano "inviate" (serve URL Inspection su campione: worker deepseek).
- Dove carica AdSense (se anche su quiz, tabelle, pagine corte).
- Quanto pesa la CMP: se non e certificata Google, il motivo del rifiuto puo essere altro e questo piano non basta da solo.
- La stima di impatto sul rifiuto non e una probabilita: e la riduzione misurabile del contenuto da modello. AdSense non dice quale soglia accetta.

---
# Revisione del 4 ottobre, sera: integrazione dei rapporti dei worker

Fonti (tutte in `/mnt/c/Users/Nilo/dev/trade5/review/`): `divarioitalia_audit_A2.md` (deepseek, CMP/CWV/link), `divarioitalia_REVISIONE_piano_B.md` e `divarioitalia_REVISIONE_metodo_audit.md` (agy), `divarioitalia_link_check/RAPPORTO.md` e `divarioitalia_ondata2_misura/RAPPORTO.md` (nemotron). I numeri dei worker non li ho rifatti, tranne dove dico.

## Fatti nuovi che cambiano il piano
1. **Schede (ondata 2)**: la misura dice (a) 229, (b) 57, (c) 30; altre 106 hanno prosa ma nessuna impressione e 19 hanno impressioni ma nessuna prosa. Quindi `noindex` per (b) tocca **57** schede, non le ~100 che stimavo, ed e sotto la soglia di 150 della spec. Le 19 con impressioni e senza prosa sono la prima fila da scrivere (ter-901 PIL pro capite e bes-04BEC002P retribuzione hanno oltre 1000 impressioni ciascuna).
2. **Link e sitemap**: 0 link rotti, 0 canonical incoerenti, 0 duplicati, 10 orfane e sono proprio le 10 varianti `?profilo=`: conferma l'ondata 1 (nessuno le linka, sono in sitemap solo per la sitemap).
3. **Annunci**: nel codice c'e solo il loader AdSense, nessuna unita pubblicitaria (`<ins class="adsbygoogle">`); lo slot banner e configurato e mai usato. Il punto "togli gli annunci dai quiz" dell'ondata 1 si riduce a documentare e a fissare la regola per quando le unita arriveranno: **nessuna unita su pagine di interfaccia o sotto 500 parole**.
4. **CMP**: Iubenda via GTM, Consent Mode v2 con tutto `denied` di default, pulsante di revoca presente. Non verificato: certificazione Google e segnale TCF v2.2 reale. La CMP e caricata da GTM, quindi senza JavaScript non c'e banner. Serve la dashboard Iubenda e un controllo live (Tag Assistant): **non lo puo fare un worker, lo fa il titolare o Cowork**.
5. **Core Web Vitals**: PageSpeed ha dato 429, le cifre sono stime di peso (home ~950 KB, regione ~600 KB, scheda ~380 KB): nessun dato LCP/CLS/INP vero. Serve una chiave PageSpeed/CrUX.
6. **Correzione a un rapporto dei worker**: A2 dice che Search Console non e raggiungibile da CLI. E sbagliato: il service account `ga4-mcp` la legge (`searchAnalytics`, `sitemaps`, `urlInspection` provati il 3/10, vedi `metriche.md` e il mio audit A1). Il campione URL Inspection si puo fare ora.
7. **Audit A1 ripetibile**: lo script esiste gia sul ramo `agenti/adsense-audit-A2` (`scripts/adsense_audit.py`, 8 test). L'ondata 2 non deve riscriverlo: parte da quel ramo (spec aggiornata).

## Che cosa accetto dalla review di agy, e che cosa no
Accetto:
- **Ordine**: CMP e regola degli annunci prima dell'arricchimento. Diventa ondata 0.5, a monte. Se la CMP non e certificata, tutto il resto non basta.
- **Blog subito**: parte in parallelo, non dopo le province. Costa tempo del titolare, non lavoro dei worker, quindi non toglie risorse alle ondate.
- **Box "Dati e metodo" su ogni pagina in sitemap** (data di estrazione, fonte primaria, limiti, firma della redazione): e un cambio di template, economico e utile per chi legge. Nuova spec `SPEC-adsense-ondata-1b-box-dati-metodo.md`.
- **Il mio criterio sul testo unico non basta**, come dice il rapporto sul metodo: contare shingle misura la varieta delle frasi, non l'informazione in piu. Lo tengo come controllo del duplicato, e aggiungo un criterio che lo script non misura e che decide una persona: lettura a campione di 10 pagine per tipo (ondata 3) con la domanda "che cosa sa il lettore dopo, che non sapeva dalla tabella Istat?".
- **Rischio "scaled content" anche con Jaccard sotto 0,5**: vero. Per questo l'ondata 3 impone fatti propri per territorio e lettura umana, e il fallback e dichiarato.

Non accetto, o con riserva:
- **`noindex` su tutte le 107 province e indice sotto 100 URL.** Le prove non lo reggono bene: (1) il rapporto cita "33 visite al mese" da Semrush, ma Search Console dice 346 clic in 28 giorni, e AdSense non fissa un minimo di traffico che io sappia; (2) soprattutto, e questa e una mia inferenza che non ho verificato con una fonte: `noindex` toglie la pagina dall'indice di Google, ma il sito resta quello che il revisore AdSense visita e vede coi suoi link. Un `noindex` da solo non cambia il giudizio sul sito, lo cambiano la rimozione, il consolidamento, un testo vero o l'assenza di annunci su quelle pagine. Per questo nelle province preferisco arricchire e togliere gli annunci, e tenere `noindex` come ultima mossa se l'ondata 3 non basta. Se Cowork vuole la linea dura, il costo e basso e si torna indietro in un commit.
- **Sostituire le 107 province con 20 report regionali**: l'idea e buona per le regioni (che sono gia le pagine piu ricche, 1180 parole uniche), ma togliere le province toglie le 100 pagine che Google gia indicizza. Resta l'opzione se l'ondata 3 fallisce.
- **Indice sotto 100 URL e rapporto contenuti editoriali/scalati 1:3**: sono numeri senza fonte. Non li adotto come criteri. Adotto il criterio di leggibilita a campione sopra e la regola degli annunci.
- Le URL delle fonti AdSense citate dal rapporto non le ho potute verificare da qui: non le uso come prova.

## Ordine aggiornato
0. Identita (ramo `agenti/identita-editoriale`): review e red team in corso, poi decisione di Cowork.
0.5. **CMP e regola annunci**: verifica manuale Iubenda/TCF (titolare o Cowork) + regola scritta nel codice (nessuna unita su interfaccia o sotto 500 parole). Blocca la ripresentazione.
1. Ondata 1: consolidare le 10 varianti, escludere i quiz (in corso su Go).
1b. Box "Dati e metodo" per pagina in sitemap (nuova spec).
2. Ondata 2: misura gia fatta, resta applicare (b) = 57 schede e scrivere le 19 con impressioni senza prosa (prosa a mano o con approvazione, non da worker).
3. Ondata 3: province e regioni, con lettura umana a campione.
4. Blog verso 30, in parallelo dal giorno 1, cadenza del titolare.

Rischi non coperti che restano: la CMP (sopra), la stima d'impatto (nessuna probabilita), e il fatto che AdSense non dice la soglia.

---
## Aggiornamento del 4 ottobre mattina: CMP superata
La direzione ha verificato la CMP dal browser (`/mnt/c/Users/Nilo/orca/direzione/VERIFICA_CMP_divarioitalia_20261004.md`: Iubenda cmpId 123, certificata Google, TCF policy version 5, banner prima del consenso). L'ondata 0.5 non e piu bloccante e la CMP esce dalle cause probabili del rifiuto: il piano si concentra sui contenuti (ondate 1, 1b, 2, 3 e blog). Residuo non bloccante per un worker economico: conferma TCF 2.3 (segmento `disclosedVendors` nella stringa TC) e presenza della CMP su 5 pagine interne a campione. Resta la regola `ads_allowed` dell'ondata 1b, che non dipende dalla CMP.
