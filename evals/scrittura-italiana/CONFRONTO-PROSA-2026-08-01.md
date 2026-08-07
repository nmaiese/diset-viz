# Confronto prima/dopo: la skill scrittura-italiana sulla prosa di progetto

Data: 2026-08-01. Branch: `fase5-prosa-confronto`. **Materiale d'analisi, non un
roll-out.** Nessun contenuto pubblicato e' stato toccato, nessun prompt d'agente
cambiato. Questo file misura se la skill `scrittura-italiana` (Fase 5 del piano)
migliora la prosa, e di quanto, su un campione rappresentativo, cosi' che la
decisione di adottarla in produzione si prenda su numeri e non a naso.

I testi grezzi del confronto stanno in
[`confronto-2026-08-01/`](confronto-2026-08-01/) (un file `_prima.txt` e uno
`_dopo.txt` per caso), col kit cieco e la chiave dei giudici.

## Il metodo, in breve

Il rischio di un confronto disonesto era doppio, ed e' stato affrontato prima di
scrivere una riga:

1. **Gli strumenti saturano proprio dove serve misurare.** Il produttore gia'
   scrive bene: su un suo articolo `prose_lint` non si muove e la rubrica sta a
   19-20 (documentato in `docs/archive/WRITING_QUALITY_PLAN.md`, Parte seconda). Per
   vedere il contributo *marginale* della skill serviva uno strumento nuovo:
   [`tic_count.py`](tic_count.py), un contatore deterministico dei tic
   dell'italiano generato che `prose_lint` non copre (avverbi in -mente,
   gerundite, bipolare, perifrasi al posto di "e'/sono", lessico di plastica,
   latinismi, incipit a cornice, ritmo piatto). E' un finder, non un giudice.
2. **La eval della skill puo' premiare cio' che il progetto vieta.** I 46 casi
   della skill vivono nel registro *testo controllato* e su 34 usano `;` o
   caporali. La precedenza (assoluti di progetto sempre) e il cancello
   deterministico stanno in [`PRECEDENZA.md`](PRECEDENZA.md).

**Tre bracci, ognuno risponde a una domanda diversa:**

| Braccio | Campione | La domanda |
|---|---|---|
| **A — valore marginale** | 2 articoli gia' completi dal produttore (`ter-1`, `dem:BIRTHRATE`, famiglie diverse) | la skill migliora cio' che il produttore gia' fa bene? |
| **B — anteprima roll-out** | 2 articoli vecchi del backlog (`ter-148`, `bes:12SER020`) | quanto vale la skill sulla prosa che oggi "sa di tradotto"? |
| **C — genere** | 1 post di blog (occupazione giovanile) | e su un pezzo lungo, con un'altra forma? |

**Le riscrittre "dopo" isolano il solo strato lingua.** Nel braccio B non ho
aggiunto link ai correlati, fonti nuove ne' le due sezioni mancanti: solo tolto i
tic e sciolto la sintassi tradotta, a parita' di fatti e struttura. Cosi' il
numero misura la skill, non il mestiere completo del produttore (che quei link,
fonti e sezioni li aggiunge, ed e' quello che porta un articolo a 19).

**Le tre guardie su ogni "dopo"** (tutte verdi):
- **identita' delle cifre:** ogni numero del "prima" ricompare nel "dopo", niente
  inventato ne' perso (`tic_count` non lo fa, l'ho verificato a parte).
- **cancello caratteri vietati:** zero `—`, `–`, `;`, `…` (campo `vietati` vuoto).
- **giudizio in cieco:** due giudici indipendenti, versioni presentate come A e B
  con assegnazione mescolata, nessuna etichetta prima/dopo, rubrica a dieci
  criteri. Accordo sul vincitore: 5 casi su 5.

## Il numero

Rubrica (media dei due giudici, su 20) e densita' di tic (`tic_count`, per mille
parole, piu' bassa e' meglio):

| Caso | Braccio | Rubrica prima | Rubrica dopo | Δ | tic/1k prima | tic/1k dopo |
|---|---|---|---|---|---|---|
| `ter-1` valore agg. agricoltura | A | 19,0 | 19,0 | **0** | 4,0 | 4,0 |
| `dem:BIRTHRATE` tasso natalita' | A | 19,0 | 19,0 | **0** | 0,0 | 0,0 |
| `ter-148` imprese innovative | B | 8,5 | 11,0 | **+2,5** | 30,3 | 0,0 |
| `bes:12SER020` banda ultraveloce | B | 8,0 | 10,0 | **+2,0** | 15,0 | 8,4 |
| blog occupazione giovanile | C | 8,5 | 16,5 | **+8,0** | 8,5 | 1,6 |

Accordo tra i due giudici: totali entro un punto su tutti i casi, stesso
vincitore su tutti e cinque. Sul braccio A la skill, applicata al livello giusto,
**non ha proposto nulla**: le due versioni sono identiche, e i giudici le hanno
segnate pari a 19 senza sapere che erano lo stesso testo.

## Che cosa dice

- **Dove la prosa "sa di tradotto", vive nel backlog e nei blog, non negli
  articoli del produttore.** I 41 articoli completi del produttore sono gia'
  italiano vero (tic 0-4/mille). I 323 articoli vecchi a due sezioni sono il
  problema: 304 su 364 chiudono un paragrafo con una domanda retorica, con tic
  fino a 30/mille. La skill colpisce esattamente quel registro.
- **Il guadagno viene dal togliere i tell da traduzione**, non da un abbellimento:
  su `ter-148` sparisce la domanda retorica di chiusura ("Conta di piu' inventare
  o saper adottare...?"), la gerundite ("adottando... cambiando"), il lessico di
  plastica ("tessuto"); su `bes:12SER020` l'hype ("cresciuta enormemente",
  "sorprendentemente", "l'infrastruttura... del futuro") e la domanda finale; sul
  blog la perifrasi ("si posiziona al vertice", "si attestano al"), il gerundio
  in apertura ("Analizzando i dati... emerge una gerarchia"), il pathos ("il dato
  piu' allarmante", "precipita al").
- **Il blog guadagna di piu' (+8) perche' aveva piu' margine nella sola lingua.**
  Gli articoli B restano a 11 e 10 perche' li ho tenuti a lingua sola: senza i
  link ai correlati (criterio 5), le fonti (criterio 9) e le due sezioni mancanti
  (criteri 2, 3), il tetto e' quello. Il produttore completo li porterebbe piu'
  in alto, ma quello e' un cambio piu' grande della skill.

## Che cosa NON dice, e i limiti

- **Non dice che la skill vale zero.** Dice che il suo valore e' sul backlog e sui
  blog, non sopra il produttore gia' completo. Le due cose non sono in conflitto:
  la skill e' una rete di lingua, il produttore un mestiere piu' largo.
- **Il residuo `bipolare: 1` su due "dopo" e' un falso positivo del finder**, non
  un tic sopravvissuto: "la copertura non e' l'uso" e "un fatto, non
  un'impressione" sono antitesi informative legittime che la dottrina della skill
  dice di preservare. E' la prova che `tic_count` e' un finder, non un verdetto.
- **Campione piccolo (5 testi).** Serve a decidere se vale la pena, non a stimare
  un guadagno medio sul catalogo. Il pattern (backlog tradotto vs produttore
  pulito) e' pero' catalogo-largo: 304 articoli su 364 hanno la domanda retorica.
- **Il giudice e' un LLM.** Concorda con se' stesso e col contatore
  deterministico, ma per "naturalezza e voce" un confronto cieco umano resterebbe
  la prova migliore.

## La domanda per l'utente (il via prima del roll-out)

Il confronto e' pronto per la tua analisi. **Non ho toccato niente di
pubblicato** e non tocchero' `producer.md` finche' non dai il via. Le strade,
quando vorrai:

1. **Roll-out sul backlog** (il valore vero): far girare la catena con la skill
   agganciata in scrittura sui 304 articoli vecchi. E' un cambio a `producer.md`,
   quindi **gated dalla skill `canary`** (giro di misura obbligatorio prima) e
   dalle eval in `evals/`. Da fare a lotti, con `tic_count` e la rubrica come
   prima/dopo di ogni lotto.
2. **Solo blog** (piu' piccolo, alto ritorno): rilavorare gli 11 post con la
   skill, dove il margine sulla sola lingua e' piu' ampio.
3. **Non adottare in produzione**, tenere la skill come strumento a mano per chi
   scrive. Anche questo e' un esito legittimo del confronto.

Attribuzione e licenza della skill (CC BY-SA 4.0, commit di origine):
[`../../.claude/skills/scrittura-italiana/ATTRIBUZIONE.md`](../../.claude/skills/scrittura-italiana/ATTRIBUZIONE.md).
