# Verifica Gate B v4.1, secondo giro: test-pipeline-infanzia-20261009

Revisore: Claude Sonnet 5.5 (Anthropic). Bozza: commit ebc9dc647f6d6589b533768068d2c7d79de6f8af, `content/posts/2026-06-30-servizi-infanzia-regioni-2023.md`, SHA256 602880e5acc600357e9a7028e90f3894b7b6015e1e3990c79b432e7dce0bb827. Data: 2026-10-09. Ricalcolo sulla versione corrente, nessun giudizio del primo giro riusato senza controllo.

## Prerequisiti
- Hash brief 0a70f335161ab1837d8d3546476b5a294330d6e86d5ebfbd98d4a0fcc9d05fe5 uguale a quello di `gate-a.md` (PASSA v4.1). Albero pulito.
- PDF locale SHA256 edf1459e... uguale al PDF scaricato dall'URL Istat oggi (last-modified 3 feb 2026). xlsx locale SHA256 3cf261ad... uguale a quello del brief.
- Commit: primo Gate B su feef63df, ritorno autore 09c0024b, preflight C-DIV ebc9dc64 (non conta come giro).
- `_parse_gate(gate-b-2.md, "gate_b", hash, 2)` restituisce `('FERMO', '1')`.

## Numeri contro PDF e tavole
| in bozza | fonte | esito |
|---|---|---|
| 31,6; 40,4; 39,1; 36,6; 19,0; 19,5 | PDF p.1-2; Tav. 1.9 xlsx | ok |
| 39,8 / 28,2, differenza 11,6; 18 celle tabella | PDF p.2 | ok |
| quasi 378.500 posti, +3,4% | PDF p.1-2; Tav. 1.9 (378.496 al 31.12.2023) | ok |
| 34,5% frequenza (con anticipatari 4,6% e ludoteche) | PDF p.3 | ok, perimetro dichiarato |
| 18,5% utenti dell'offerta comunale 2023 | PDF p.3; Tav. 1.6 Italia 18,5 | ok, perimetro dichiarato |
| LEP 33% entro 2027 | PDF p.2 e nota i: «a livello di comune o di bacino territoriale locale» | cifra ok, livello non dichiarato in bozza |
| 45% UE 2030 | PDF p.1-2 (frequenza); Consiglio UE | pagina Consilium 403 anche oggi, corroborato dal PDF |
| 59,5% / 49,1%, circa 3.000 servizi | PDF p.5 e nota iv (terza edizione) | ok |
| 28,9% / 19,9% / 21,3% «dei servizi» | PDF p.5, «nel 28,9% dei casi rimane inevaso oltre un quarto delle domande» | base errata (vedi sotto) |
| Commissione UE: barriere posti, costi, procedure | pagina aperta, «Last updated 20 March 2026» | ok, dato Italia assente come dichiarato |

Base di 28,9/19,9/21,3: il PDF scrive «le domande insoddisfatte superano il 10% in quasi il 70% dei casi e superano il 25% nel 22,9% dei casi». Se i casi fossero tutte le strutture campionate, «oltre il 10%» non potrebbe superare il 59,5% che ha almeno una domanda non accolta. Quindi la base sono le strutture con domande non accolte. La bozza scrive «il 28,9% dei servizi», cioè tutti. Il mio rilievo del primo giro suggeriva la stessa formula («28,9% di strutture»): ricalcolata ora, non regge.

Assoluti: 378.496 / 0,316 = circa 1,198 milioni di residenti 0-2 (due valori arrotondati, non fonte). Le tavole non danno i residenti né il rapporto precedente: «non riportato» in bozza è vero.
Medie: media semplice dei cinque totali 30,92 contro 31,6 ufficiale, la bozza usa 31,6 come «Italia ufficiale».
Data: l'intestazione del PDF dice «2 FEBBRAIO 2026», il file è creato e caricato il 3 febbraio. La bozza dice 2026-02-03.

## Guardia
`guardia_articolo --json`: 0 errori, 19 avvisi, 12 non verificabili. 18 avvisi G4 sono righe della tabella (unità nel titolo «Posti per 100 bambini di 0-2 anni»), 1 è la nota «Italia ufficiale». Non verificabili: 34,5, 18,5, 378.500, 28,9, 19,9, 21,3, 3.000 sono nel PDF (28,9/19,9/21,3 con base sbagliata); 5 G1 sull'anno della media non pertinenti (31,6 è ufficiale). Nessuno dei 7 valori è nel registro del brief.

## Test e resa
- `unittest tests.integration.test_blog_trend_articles tests.integration.test_blog_indicator_links`: 23 test OK.
- gunicorn locale 127.0.0.1:5078, Chrome (Playwright, canale chrome) a 375 e 1100 px, chiaro e scuro: `/blog/servizi-infanzia-regioni-2023` 200, `data-v1="articolo"`, copertina `art-hero` con credito «Immagine: Redazione Divario Italia, CC BY 4.0, via Divario Italia», due figure `art-fig`, `scrollWidth` uguale alla larghezza in tutti e quattro i casi (nessun overflow), sfondo scuro corretto in dark. Nessuna «Foto», nessuna «medie semplici non ponderate», nessuna `art-lead`.
- Figure a 375 px: viewBox 720 reso a 343 px, righe `fig__meta` da 13 unità, circa 6 px a schermo, quindi unità, campione, fonte e nota delle figure non si leggono. Intestazione della prima tabella ancora resa come elenco «Ripartizione, Capoluoghi, Altri comuni, Totale».
- `indicator_role: related`: il link a ter-414 è valido (`/indicatore/presa-in-carico-di-tutti-gli-utenti-dei-servizi-per-l-infanzia/ter-414`) e il blocco «L'indicatore in parole semplici» non compare. Il riquadro «Continua a esplorare» mostra comunque «Presa in carico di tutti gli utenti ... 20,4% nel 2023, media semplice delle regioni con il dato»: etichettato come media semplice, non detta nazionale.
- Template su altri articoli: reddito pro capite (foto Santeri Viinamäki, CC BY-SA 4.0) e figli per donna (foto Patafisik, CC BY-SA 4.0) rendono «Immagine: autore, licenza, via Wikimedia Commons. Ritagliata e ridimensionata.»: vero. La nota «medie semplici non ponderate» in «Dati e metodo» è sostituita ovunque da una frase generica: non falsa, ma toglie un avviso.
- `date_modified` nel frontmatter non è letto (`app/blog.py` usa `updated`): la pagina dice «Ultima verifica editoriale il 30 giugno 2026».
- Coerenza famiglia: `content/indicators/414.md` («va al nido il 40,5% dei bambini», «copertura reale») in contrasto col perimetro Istat usato dall'articolo.

## Non provato
Pagina Consiglio UE (403). Pubblicazione effettiva Istat al 3 febbraio (il PDF porta 2 febbraio in copertina).
