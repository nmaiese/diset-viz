# Verifica Gate B v4.1: test-pipeline-infanzia-20261009

Revisore: Claude Sonnet 5.5 (Anthropic). Bozza: commit feef63dfc384b9c1c19eaed3385bcc523a1cf6b8, `content/posts/2026-06-30-servizi-infanzia-regioni-2023.md`, SHA256 208c6ed2c5710b2a3fad092316058fd2abda5ec756e79c0d44c32fb8672d90a0. Data: 2026-10-09.

## Prerequisiti
- Hash brief corrente 0a70f335161ab1837d8d3546476b5a294330d6e86d5ebfbd98d4a0fcc9d05fe5 = Hash brief di `gate-a.md`; SHA brief 491e7adb.
- `_parse_gate(gate-a.md, "gate_a", hash brief)` restituisce `('PASSA', '')`: Gate A v4.1 valido.
- Albero pulito, HEAD feef63df. Il Gate B non era mai stato eseguito: i «rilievi Gate B» di 22b87b33 sono preflight C-DIV e non contano come giro.

## Ricalcoli contro il PDF (copia locale SHA256 edf1459e..., identica al PDF scaricato dall'URL Istat il 2026-10-09, 1.062.319 byte)
| numero in bozza | PDF Istat | esito |
|---|---|---|
| 31,6 posti ogni 100 residenti 0-2 | p.1 e p.2, «in media ci sono 31,6 posti ogni 100 bambini» | ok |
| ripartizioni 36,6 / 39,1 / 40,4 / 19,0 / 19,5 e capoluoghi/non capoluoghi | tabella p.2, tutte le 18 celle uguali | ok |
| 39,8 e 28,2, differenza 11,6 | p.2 «una differenza di 11,6 punti percentuali» | ok (39,8-28,2 = 11,6) |
| quasi 378.500 posti, +3,4% | p.1 e p.2 | ok |
| crescita del rapporto in parte per calo del denominatore | p.2 «in parte anche per effetto del calo delle nascite» | ok |
| 59,5% nidi e sezioni primavera con domande non accolte; 49,1% nel 2021/2022 | p.5, indagine campionaria su circa 3.000 servizi (nota iv, terza edizione) | cifra ok, descrizione in bozza no (vedi sotto) |
| 45% nel 2030 | PDF p.1/p.2: target di frequenza 2030; Consiglio UE 2022-12-08 | ok come partecipazione. La pagina Consilium risponde 403 al revisore (curl e WebFetch): il claim è corroborato dal PDF Istat, non riaperto alla fonte UE |
| Commissione UE, 39,3% nel 2024, barriere posti/costi/procedure | pagina aperta, «Last updated: 20 March 2026»; nessun dato Italia | ok, la bozza non usa il 39,3% |

Medie: media semplice dei cinque totali 30,92 (Istat 31,6), dei capoluoghi 37,14 (39,8), dei non capoluoghi 27,98 (28,2). La bozza usa correttamente 31,6 «Italia ufficiale».
Assoluti (REV §4): 378.500 / 0,316 = circa 1,198 milioni di residenti 0-2; posti 2022/2023 circa 366.050 (+12.450, il PDF dice «circa 12.500»). La bozza non riporta né il numero dei bambini né il suo calo né il rapporto precedente: cita solo +3,4% e «calo del denominatore».

## Dati nel PDF che la bozza non usa
- p.3: frequenza dei bambini 0-2 in una struttura educativa 34,5% (incluso il 4,6% di anticipatari alla scuola dell'infanzia e ludoteche), 2023/2024. Posti 31,6 e frequenza 34,5 sono grandezze diverse con la frequenza più alta: la dimostrazione concreta della tesi del brief, assente dal testo.
- p.3: utenti dell'offerta comunale 221.500 nel 2023, 18,5% dei residenti 0-2, minimo 5,9% Calabria, massimo 40,5% Friuli-Venezia Giulia.
- LEP 33% di posti entro il 2027 (31,6 «poco al di sotto»): il riferimento italiano pertinente ai posti, assente. La bozza cita solo il 45% UE di partecipazione.
- p.9: tasso di risposta dei Comuni 79,9% nel 2023/2024, mancate risposte stimate; nessuna dicitura «definitivo» in tutto il PDF.

## ter-414 (tassello dichiarato nel brief)
Serie interna 2023: Calabria 5,92, Friuli-Venezia Giulia 40,50. Sono gli stessi estremi che l'Istat attribuisce a «utenti dell'offerta comunale» (iscritti a servizi pubblici o privati convenzionati e beneficiari di contributi comunali, 18,5% a livello nazionale). Media semplice delle 20 regioni 20,43. La bozza (commit 22b87b33) ha tolto «dai Comuni» e definisce la misura «presa in carico di tutti gli utenti» di nidi e servizi, senza il perimetro comunale. Coerenza famiglia: la scheda `content/indicators/414.md` dice «va al nido il 40,5% dei bambini» e «La media è del 20%», lettura che contraddice la bozza (frequenza diversa da presa in carico) e il perimetro Istat.

## Figure: ricalcolo geometrico
Scala fig. 1: 9 px per punto, 0-60 su 540 px. Barre 49,9=449,1; 33,4=300,6; 47,3=425,7; 36,1=324,9; 44,8=403,2; 33,5=301,5; 39,8=358,2; 28,2=253,8; 20,7=186,3; 19,0=171,0; 23,0=207,0; 17,9=161,1: tutte coerenti col dato. Fig. 2: 59,5=535,5; 49,1=441,9, coerenti. Copertina PNG: scala 14,85 px per punto, 40,4=600; 31,6=469,3; 19,0=282,2, coerenti; le etichette usano il punto decimale («40.4»), non la virgola.
Dati figura 1 = CSV `app/static/data/articles/servizi-infanzia-regioni-2023.csv` = tabella nell'articolo = tabella Istat p.2. Il CSV non ha unità nelle colonne Capoluoghi e Altri comuni.

## Resa locale (gunicorn 127.0.0.1:5077, Chrome headless, 1100 px chiaro e scuro)
- `data-v1="articolo"`, 200. Copertina `art-hero` presente con `<img>` e caption. Nessun `.art-lead`, nessuna striscia «una regione del Mezzogiorno su otto»: ok.
- Due figure in linea (`art-fig`), leggibili in chiaro e in scuro. I fill delle barre sono esadecimali cotti nell'SVG (`#a75001`, `#666`) e l'arancio, accento dell'interfaccia, è usato come colore dei dati (capoluoghi): contro CLAUDE.md.
- La copertina è un raster su fondo bianco, resta bianca in scuro.
- Prima tabella: header «Ripartizione, Capoluoghi, Altri comuni, Totale» reso come elenco spezzato sopra le righe a schede; nessuna unità né didascalia. Seconda tabella normale.
- Credito copertina reso: «Foto: Redazione, Proprietaria, via Wikimedia Commons.» per un grafico proprio.
- Blocco «Dati e metodo»: «L'analisi confronta territori di peso diverso: le medie sono medie semplici non ponderate» (non vale per questo pezzo), «L'indicatore in parole semplici ... Un valore di 20 indica ... 20%» (testo generico di ter-414), «Ultima verifica editoriale il 30 giugno 2026» (data precedente alla revisione), Territori «Italia».
- 375 px: NON PROVATO. Chrome headless ritaglia a destra anche una pagina di controllo (`figli-per-donna-regioni-italia`), quindi lo screenshot a 375 non è affidabile; l'iframe è bloccato da `frame-ancestors 'self'` e il tentativo CDP non è terminato. Giudico a 375 solo ciò che si legge nei file (SVG viewBox 720 con righe meta lunghe e `font-size` 12, tabella a schede).
