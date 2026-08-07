# Il bersaglio della prosa: dal ritmo alla leggibilita'

Data: 2026-08-04. Segue e non sostituisce
[`CONFRONTO-PROSA-2026-08-01.md`](CONFRONTO-PROSA-2026-08-01.md), che misurava un
asse diverso (i tic lessicali dell'italiano generato) e resta valido.

## Da dove nasce

Un utente ha letto la pagina di `ter-167` (intensita' di accumulazione del
capitale) e l'ha giudicata "estremamente macchinosa e difficile da leggere, si
vede che e' tradotta in inglese". Ha allegato una propria riscrittura che
conserva **tutte** le cautele fattuali dell'originale.

La diagnosi ovvia era che la prosa fosse sfuggita ai controlli. Misurando, si e'
rivelata falsa.

## Il numero che ha ribaltato la diagnosi

`tic_count.py` sui due testi, piu' il conteggio delle virgole per frase:

| | ter-167 pubblicato | riscrittura utente |
| --- | --- | --- |
| tic per 1000 parole | **2,2** | **12,5** |
| avverbi in -mente | 0 | 5 |
| gerundite | 0 | 3 |
| burstiness | **0,46** | **0,28** |
| virgole medie per frase | 1,49 | 1,69 |

Il testo giudicato piu' leggibile perde su ogni metrica. E la rubrica avrebbe
fatto lo stesso: il criterio 8, `Ritmo e imperfezione`, dava 0 a "periodare
uniforme" e 2 a "ritmo vero, sezioni di peso diverso". La riscrittura preferita
e' **piu' uniforme**.

`ter-167` inoltre non era prosa sfuggita a niente: 2,2 tic/1000 lo mette dentro
la fascia "produttore pulito" (0-4) documentata nel confronto del 1 agosto, e il
verificatore lo aveva ricontrollato lo stesso 4 agosto, 19 affermazioni, tutte
confermate, esito pulito.

**Quindi il difetto non era nell'esecuzione, era nel bersaglio.** Il produttore
centrava esattamente cio' che gli era scritto.

## Che cosa era davvero rotto: l'impilamento

Non il ritmo. Piu' idee dentro una frase sola, tenute insieme dalle virgole. Da
`ter-167`:

> "In alto due regioni si staccano, la Basilicata e il Piemonte, e fra il
> Piemonte e la terza, la Valle d'Aosta, corrono gia' due punti e mezzo, il salto
> piu' largo dell'intera graduatoria."

Tre idee, cinque virgole, una frase. Nessuna regola violata, e il lettore torna
indietro. Si puo' variare il ritmo scrivendo frasi che si prendono al primo
passaggio: le due cose non erano mai state in conflitto, ma solo una delle due
era premiata.

## La controprova che chiude la questione sullo strumento

Raccogliendo `content/esempi/`, dieci testi veri di testate italiane scelti solo
perche' si leggono al primo passaggio, il contatore li ha misurati cosi':

| testo | tic/1000 | parole per frase | leggibile? |
| --- | --- | --- | --- |
| Openpolis, aree interne | **21,4** | 17,5 | si' |
| Openpolis, Abruzzo | **18,9** | 19,3 | si' |
| Istat, BesT regionali | 13,8 | **32,1** | **no, scartato** |
| Istat, conti territoriali | 10,6 | 31,5 | si' |
| lavoce.info, salari Sud | **0,0** | 15,1 | si' |
| Info Data, mortalita' | **0,0** | 17,8 | si' |
| `ter-167` pubblicato | 2,2 | 21,7 | **no, e' il caso** |

Prosa professionale che lo strumento boccia (Openpolis, dieci volte il nostro
articolo illeggibile), prosa faticosa che lo strumento promuove (`ter-167`). Non
e' un difetto del contatore: misura il lessico dell'italiano generato e lo misura
bene. E' la prova che **lessico e leggibilita' sono due assi diversi**, e che
sul secondo nessuna metrica esistente in questo repository dice il vero.

Corollario operativo, gia' scritto in `docs/WRITING_RUBRIC.md` e in
`content/STYLE.md`: sotto il bersaglio nuovo `mente` e `gerundite` possono salire
legittimamente, `burstiness` non e' ne' un bene ne' un male, e **il solo campo
duro che esce da `tic_count.py` resta `vietati`.**

## Che cosa e' cambiato

| file | cambio |
| --- | --- |
| `docs/WRITING_RUBRIC.md` | criterio 8 da `Ritmo e imperfezione` a `Leggibilita'`, piu' la sezione che spiega il cambio e il pavimento anti-singhiozzo. Gli altri nove criteri **intatti**. |
| `content/STYLE.md` | la mossa "Varia il ritmo" diventa "Un'idea per frase" con prima/dopo; "Imperfezione controllata" mette la leggibilita' prima della voce e da' al caveat la sua frase; la precedenza sulla skill esterna copre ora la dottrina, non solo i caratteri. |
| `.claude/agents/producer.md` | passo 4: si sceglie un modello da `content/esempi/` prima di scrivere. Passo 5: l'ultimo atto e' una rilettura ad alta voce contro quel modello. Piu' la precedenza della leggibilita' sulla banda 500-700 parole. |
| `content/esempi/` | **nuova**, dieci estratti verbatim da otto testate, con indice per forma di storia. |

Il rigore non e' stato toccato: brief unica fonte dei numeri,
`definition_check.py`, classi di errore `indicator-review`, fonti verificate una
per una, firma con `reviewed_vintage`, verificatore a valle. Nessuna riga di
quelle e' cambiata.

## Il canary

Metodo identico alle righe precedenti: subagent su `opus` con le istruzioni reali
(`producer.md` aggiornato piu' STYLE, rubrica, skill), fixture e brief congelati,
niente dati vivi ne' web, senza l'hook di perimetro.

| eval | baseline | candidato | esito |
| --- | --- | --- | --- |
| writer | ok (0 cifre fuori brief, 0 caratteri vietati) | **ok**, `cifre_fuori_brief: []`, `problemi: []` | pari |
| reviewer | 7/7 errori piantati trovati | **7/7**, `mancati: []` | pari |
| verifier | 12/12 | n/a | il verificatore non e' toccato |
| admissions | 11/11 | n/a | l'ammissione non e' toccata |
| metro | | `score_eval.py --self-test` **ok** | integro |

**Che cosa questo prova, e che cosa no.** Le due eval contano cifre fuori dal
brief, caratteri vietati ed errori piantati: misurano il **rigore**, e dicono che
non e' regredito. Non vedono la leggibilita' e non possono dire se la prosa e'
cambiata. Quella e' la domanda del confronto cieco qui sotto.

### Il testo prodotto in eval, misurato

Contro l'articolo che ha aperto il caso:

| | `ter-167` pubblicato | writer eval sotto le regole nuove |
| --- | --- | --- |
| parole per frase | 21,7 | **16,1** |
| virgole medie per frase | 1,49 | **1,06** |
| tic per 1000 parole | 2,2 | 0,0 |
| burstiness | 0,46 | 0,35 |
| `vietati` | vuoto | vuoto |

La burstiness scende, ed e' atteso: era il vecchio punteggio, ora e' un effetto
collaterale neutro.

### Nota di onesta' sulla misura

La precedenza della leggibilita' sulla banda 500-700 parole e' stata scritta in
`producer.md` **dopo** che la eval writer era girata, in risposta a un attrito
che l'agente stesso ha segnalato. Il prompt misurato non e' percio' identico al
prompt che si fonde. L'aggiunta non puo' muovere il punteggio, perche' la eval
writer conta cifre fuori dal brief e caratteri vietati e la nota non tocca ne'
gli uni ne' gli altri, ma vale dirlo invece di lasciarlo passare.

## Il confronto cieco: i due giudici non sono d'accordo, e va letto per intero

Due giudici indipendenti, `opus`, con **assegnazione invertita fra loro** (per il
primo il pubblicato era A, per il secondo era B), i dieci criteri della rubrica
emendata, nessuna etichetta prima/dopo, divieto esplicito di cercare i file nel
repository. Il rigenerato e' un **dry run in scratchpad**, mai scritto in
`content/indicators/`.

| | pubblicato | rigenerato |
| --- | --- | --- |
| giudice 1 | **17/20** | 14/20 |
| giudice 2 | 17/20 | **18/20** |
| media | **17,0** | 16,0 |
| **criterio 8, Leggibilita'** | **0 e 0** | **1 e 2** |

**Sul vincitore non concordano. Sulla diagnosi concordano del tutto.**

### Su che cosa concordano, ed e' la parte che conta

**Il criterio 8: il pubblicato prende zero da entrambi.** Non un uno, uno zero,
due volte, in cieco, con assegnazioni invertite. E i due giudici citano
**gli stessi tre periodi** come prova, senza essersi parlati:

- il periodo su Basilicata e Piemonte, tre idee e cinque virgole,
- la cautela sul nome, ventuno parole di apposizione fra il verbo e il suo
  complemento, piu' le "986 righe dell'archivio unico" che il giudice 2 chiama
  "idraulica interna",
- "fermo al 2022", una cautela metodologica agganciata con due virgole dentro
  una frase di correlazione, che e' esattamente il difetto che
  `content/STYLE.md` ora chiama per nome.

Il giudice 1: "in A l'inciampo e' sintattico e ricorrente". Il giudice 2: "non
per un caso isolato". La direzione del cambio non e' in discussione fra loro.

**Il pavimento anti-singhiozzo funziona.** Il giudice 1 ha dato al rigenerato
**1 e non 2** proprio perche' un paragrafo "non nasce da quello prima e non porta
a quello dopo, e' un elenco di posizioni travestito da paragrafo". E' la clausola
che ho aggiunto alla colonna dello zero, e un giudice l'ha applicata contro il
testo nuovo senza che nessuno gliel'avesse chiesto.

**La perdita di contenuto, e la stessa identica.** Entrambi vedono che il
rigenerato ha perso la forma della serie (picco 2007, nove anni sotto il 1995,
fondo 15,17 nel 2014) e che l'ha titolata **"Ventotto anni di salita"**. Il
giudice 2 e' il piu' duro, e ha ragione: "il titolo dice una cosa che il corpo
del testo non sostiene", perche' lo stesso paragrafo scrive che l'ultimo anno ha
mosso la media piu' dei ventisette precedenti. **Fuorviante per omissione**, e
per il giudice 2 e' "il difetto piu' grave dei due testi, piu' grave di qualsiasi
frase impilata".

E' la lacuna del brief, non un difetto della prosa: quelle cifre non esistono nel
brief e la regola le vieta.

### Su che cosa non concordano, e perche' e' legittimo

Il disaccordo e' su **quanto pesa una perdita di contenuto contro un guadagno di
leggibilita'**, ed e' un giudizio editoriale vero, non un errore di misura.

- Il giudice 1: "i difetti di A costano un'ora di forbici, quelli di B costano un
  ritorno ai dati", quindi tiene il pubblicato.
- Il giudice 2: sul criterio 8 "non e' un vantaggio di sfumatura, e' 2 contro 0",
  quindi pubblica il rigenerato, a tre condizioni.

**Le condizioni sono le stesse per entrambi**, ed e' il vero esito del confronto.
Il giudice 1 lo scrive cosi': *"L'articolo giusto non e' nessuno dei due. E' il
contenuto di A dentro la sintassi di B."*

### Un errore del giudice 2, verificato a mano

Il giudice 2 sostiene che sia il **rigenerato** a portare due cautele che il
pubblicato non ha ("se viene da molte operazioni diffuse o da pochi cantieri
grandi" e "il rendimento futuro di quel capitale qui non si vede"). E' il
contrario: quelle due frasi stanno nel **pubblicato**, e il rigenerato le ha
perse, tenendo solo edilizia contro macchinari. Il giudice 1 l'aveva visto
giusto ("Nessuna delle due e' in B").

Non sposta il risultato portante, che e' l'unanimita' sul criterio 8 con gli
stessi periodi citati, ma va corretto: un giudizio che si usa come prova si
ricontrolla, e questo non reggeva. Conta anche come limite del metodo: due
giudici LLM concordano sulla diagnosi e sbagliano la contabilita' di quello che
un testo contiene.

### Due difetti del rigenerato che nessuno dei due ha perdonato

- **Ha ripetuto il disclaimer sulla media non ponderata**, che `content/STYLE.md`
  vieta espressamente perche' l'apparato della pagina lo porta gia'. Colpa
  dell'istruzione che ho dato al dry run, dove l'ho elencato fra le cautele
  obbligatorie: non e' una cautela da scrivere, e' una da non sbagliare. Le
  istruzioni fuse non hanno questo difetto.
- **"986 righe dell'archivio unico"** sopravvive dal pubblicato ed e' gergo di
  retrobottega. Il rigenerato l'ha migliorato ("valore per valore e anno per anno
  dal 1995") ma non del tutto.

### Un difetto trovato per caso, sulla pagina viva

Il giudice 2 ha notato che nel paragrafo della cautela sul nome gli accenti sono
scritti con l'apostrofo ASCII ("non si puo'", "e'", "intensita'") mentre tutto il
resto dell'articolo usa gli accenti veri, e l'ha scartato come una cucitura del
kit. Non lo era: e' **cosi' nel file committato**, quindi cosi' sulla pagina
pubblicata. Difetto reale, indipendente da questo lavoro, da correggere.

## Che cosa si conclude

**Il cambio di bersaglio passa, e la rigenerazione degli articoli esistenti no,
non ancora.**

- Il cambio di prosa **funziona**: criterio 8 da 0 e 0 a 1 e 2, in cieco, con gli
  stessi periodi citati come prova da due giudici indipendenti. Le eval congelate
  dicono che il rigore non si e' mosso.
- Ma **rigenerare oggi un articolo su una serie lunga baratta leggibilita'
  contro contenuto**, perche' il brief non regge la `dinamica`, e per un giudice
  su due quel baratto e' in perdita.

Quindi: le istruzioni nuove valgono da subito per gli articoli **nuovi**, dove
non c'e' niente da perdere. La coda dei 33 articoli completi del produttore
**resta ferma** finche' `indicator_brief.py` non emette la serie annuale della
media, con il suo giro di canary. Il rientro non parte da solo, perche' e'
guidato da `reviewed_vintage` contro `vintage` e non da un cambio di rubrica:
nessun articolo si invalida a sorpresa.

## Gli attriti che gli agenti hanno segnalato

Raccolti dai due giri di eval, separati fra quelli introdotti da questo cambio e
quelli preesistenti.

**Introdotti qui, uno, chiuso.** Spezzare aggiunge parole, e la banda "500-700
parole" di `producer.md` tirava contro il criterio 8 senza una precedenza
dichiarata (l'agente e' finito a 737). Risolto: la banda e' indicativa e sulla
leggibilita' perde, si taglia una ripetizione e mai una cautela.

**Introdotto qui, uno, aperto.** Il criterio 8 non ha nessuno strumento, e la
rubrica lo dice apertamente. L'agente writer si e' ancorato da solo alle
parole-per-frase dell'estratto scelto (17,8) come soglia: e' un metro che si e'
inventato, ed e' anche il segno che la libreria funziona come ancora. Il confine
fra "spezzato" e "sminuzzato" resta a occhio.

**Preesistente, e il piu' grosso dei cinque: il brief non regge la `dinamica`.**

Riscrivendo `ter-167` il produttore ha dovuto **tagliare** il picco del 2007, il
fondo del 2014 (15,17) e i nove anni sotto il livello del 1995, cioe' la forma
della curva su ventotto anni. Non per prudenza eccessiva: il blocco `ANDAMENTO`
di `scripts/indicator_brief.py` (righe 549-562) emette la media del primo anno,
quella dell'ultimo, la variazione, il trend del divario e il delta massimo e
minimo per territorio. **Non emette la serie annuale della media.** Quelle tre
cifre non hanno provenienza dal brief, e la regola "il brief e' la sola fonte dei
numeri" le vieta.

Il fatto che l'articolo pubblicato le contenga vuol dire che qualcuno le ha prese
altrove, e che il verificatore le ha confermate perche' lavora contro i dati vivi
e non contro il brief. Non e' un errore di fatto, e' un buco nel perimetro.

Il costo editoriale e' reale: su una serie lunga la storia **e'** la forma della
curva, e oggi il produttore puo' dire solo da dove parte e dove arriva. E' la
lacuna piu' seria trovata in questo giro, non e' causata da questo cambio, e la
correzione e' una manciata di righe in `indicator_brief.py` (la media per anno,
il massimo e il minimo della serie delle medie con il loro anno) piu' un giro di
canary suo, perche' arricchire il brief cambia quello che un articolo puo' dire.

**Preesistenti, minori, segnalati per il prossimo giro sul metro.**

- La classe `universale` di `indicator-review` non copre pulitamente le
  affermazioni sulla **forma** della distribuzione ("i valori scendono con
  gradualita'"): e' scritta per gli avverbi di universalita', e il controesempio
  sta nel blocco SALTI, non in SI MUOVONO CONTROCORRENTE.
- Un falso aritmetico contro la serie ("piu' che dimezzato" su un divario che si
  e' ristretto di 0,92 punti) non ha una classe: cade nelle regole puntuali senza
  flag.
- `prose_lint.py --show` legge `content/indicators/` ed e' percio' irraggiungibile
  in eval: la meta' automatica del criterio 10 resta scoperta li'. L'agente l'ha
  coperta con `tic_count.py`, che accetta un path qualsiasi.
- Il brief stampa gli `h2` dell'articolo esistente sotto STATO DELL'ARTICOLO.
  Riusarli e' la via piu' comoda e vanificherebbe la eval in silenzio, e in
  produzione produce il timbro che `content/STYLE.md` vieta. `producer.md` non
  mette in guardia.
- L'autovalutazione sui dieci criteri satura (l'agente writer si e' dato 20/20),
  come `docs/archive/WRITING_QUALITY_PLAN.md` gia' segnalava. Il numero utile viene da
  fuori.
