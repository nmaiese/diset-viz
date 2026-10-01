# Studio dei testi: titoli, CTA, landing page

Redatto il 1 ottobre 2026. È uno **studio**: nessun testo del sito è stato modificato. Serve a decidere che cosa implementare, e in che ordine.

Il lavoro è stato diviso fra tre worker Orca (due claude sonnet, un antigravity; nessun Codex, come chiesto) e i dati di prima mano raccolti da chi coordina. Il materiale grezzo dei worker sta nei loro worktree (`studio-testi-audit`, `studio-testi-trend`, `studio-testi-competitor`, file `lavoro/RAPPORTO.md`), fuori dal ramo.

## 1. Come è stato verificato, e quanto fidarsi

| Fonte | Che cosa è | Affidabilità |
| --- | --- | --- |
| Corpus testi | Title, meta, H1, H2, CTA, nav di 28 pagine, estratti dall'HTML di produzione il 1/10/2026 | Alta: dato di prima mano |
| Search Console | 90 giorni, 1 lug - 28 set 2026, via service account | Alta, ma campione piccolo: 614 clic, 19.660 impressioni, CTR 3,1%, posizione media 8,0 |
| Semrush `it` | Keyword organiche e concorrenti per keyword in comune | Media: rilevazioni a campione, posizioni più basse di GSC (PIL pro capite: Semrush 14-21, GSC 8,5) |
| Audit interno (claude) | 13 tipi di pagina, 18 incoerenze, test del repo | Alta. Ricontrollati a campione `classifica.html:32`, `nav.py:33-34`, `Eta media` nel manifest, `seo_titles.DESCRIPTION_MAX`: tutti esatti. Non ha eseguito la suite |
| Trend e SEO (claude) | Documentazione Google, Backlinko, Zyppy, Pew, NN/g, WCAG | Buona. Ricontrollate due citazioni (Backlinko 15,5% vs 16,3% non significativo; Google "no additional requirements" per AI Overviews): esatte. Dichiara onestamente ciò che non ha letto |
| Competitor (antigravity) | 17 siti | **Citazioni letterali buone** (ricontrollate Lab24, Openpolis, Tuttitalia, Truenumbers, Pagella Politica). **I conteggi dei pattern ("12 su 17") e i rinvii a righe non sono affidabili**: i totali non tornano e molte H1 sono "non verificato". Uso solo le citazioni e le osservazioni qualitative |

## 2. Che cosa dicono i dati

1. **La posizione domina, il testo conta poco.** CTR per scheda: 1,4% a posizione 8,5 (PIL pro capite), 7,9% a posizione 5,5 (disoccupazione). La differenza segue la posizione (Backlinko, 4 milioni di risultati: primo risultato 27,6% di CTR). Con 614 clic in 90 giorni **nessun cambio di title è misurabile**.
2. **Le formule "da clic" sono mito o incerte.** Domanda contro affermazione: 15,5% contro 16,3%, non significativo. Title di 40-60 caratteri, +33% di CTR, ma è correlazione. Google non dà soglie ufficiali di lunghezza e la meta description non è un fattore di ranking.
3. **Google riscrive il 61,6% dei title** (Zyppy, 80.959 title, 2022), e di più quando title e H1 divergono. Questo è l'argomento SEO più concreto per allineare title, H1 e og:title.
4. **AI Overviews: nessuna ottimizzazione speciale** (Google, documentazione ufficiale). Pew: con riassunto AI i clic scendono da 15% a 8% (USA, marzo 2025). Per un sito di dati l'implicazione è di prudenza: un title che regala il numero nudo toglie la ragione di cliccare. Conseguenza (inferenza): promettere classifica, confronto, serie.
5. **La domanda reale è generica.** Semrush: "pil pro capite" (2.400 ricerche al mese), "pil pro capite italia" (3.600), "provincia di chieti" (4.400), "terni provincia" (2.400), tutte in posizioni 14-77. Chi cerca vuole il dato e il confronto, non la tesi.
6. **URL legacy ancora vive in Search Console.** `/indicatore/281-tasso-di-omicidi` ha 19 clic, più del canonico (17). Idem `901-pil-pro-capite` (367 impressioni). Il 301 c'è: è un problema di consolidamento, **non di testo**. Si guarda con l'ispezione URL, non si tocca.
7. **Sul sito la lacuna di messaggio è l'uniformità, non la creatività.** Le meta con i due estremi veri sono il punto forte (nessun competitor letto lo fa). Le incoerenze interne sono invece misurabili.

## 3. Competitor: che cosa ricaviamo

Citazioni verificate (1/10/2026):

- **Lab24 / Il Sole 24 Ore**, qualità della vita: title `Qualità della vita 2025: la classifica delle province italiane dove si vive meglio. Trento la migliore nel 2025 | Il Sole 24 ORE`, meta `Qual è la provincia dove si vive meglio in Italia? ...`. Anno, parola "classifica", la formula "dove si vive meglio" e il vincitore. È il concorrente diretto per la nostra pagina qualità della vita, e usa la forma che la gente cerca.
- **Tuttitalia**: `Regione Lombardia - Guida ai comuni e alle province`, H1 `Regione Lombardia`. Nome del luogo in testa, brevissimo, categoria dopo. Pagine di territorio con tono enciclopedico.
- **Openpolis**: `Openpolis: Liberiamo, raccogliamo e curiamo i dati in Italia`. Promessa di lavoro, non di contenuto.
- **Truenumbers**: `Truenumbers - Il data journalism dei veri numeri`. Tono assertivo, "REALI" in maiuscolo: l'opposto della nostra voce.
- **Istat, Eurostat, Noi Italia**: title e H1 quasi nudi (`Istat`, `Home`), nessuna proposta di valore.

Spazi liberi (inferenza motivata): nessuno dei siti letti mette in meta i due estremi con i territori; nessuno dichiara limiti del dato accanto a una classifica; non abbiamo visto CTA di download dati sulle schede dei giornali. La nostra voce sobria "Cronaca" è un vantaggio da conservare, non da addolcire verso il clickbait.

**Cosa copiare**: la parola "classifica" e la formula "dove si vive meglio" nel title qualità della vita; l'anno quando il dato è annuale. **Cosa non copiare**: le maiuscole enfatiche, le domande-esca, il vincitore nel title se la classifica ha profili (nostro caso).

## 4. Come dovrebbero essere scritti: i criteri

Derivati dal corpus e dai dati, non da opinione. Il grado di evidenza esterna è indicato.

- **Title** (budget 60 del repo): prima la parola che la persona cerca ("classifica", il nome della misura), poi il livello o il dato, poi un numero se avanza spazio. Il nome del sito non serve nella SERP. Una sola convenzione di marca. *Evidenza esterna debole: la lunghezza non ha soglia ufficiale.*
- **Allineamento**: title, H1 e og:title dicono la stessa tesi, anche se in forme di lunghezza diversa. Oggi nel blog sono tre testi diversi. *Motivo A (Google usa H1 e og:title per costruire il title link).*
- **Meta**: una frase-risposta con i due estremi veri e i territori, poi cosa si trova nella pagina. Tra 110 e 155 caratteri. Una definizione va nella pagina, non nella meta. *Non è leva di ranking: è vetrina.*
- **H1**: o l'etichetta neutra della cosa (schede), o la tesi (articoli, divari), mai due tesi. Sotto i 90 caratteri.
- **Sottotitolo**: perimetro (cosa, fonte, anno), non una ripetizione dell'H1.
- **CTA**: verbo + oggetto che dice dove porta. Un'etichetta di stato non è una CTA. Una destinazione, un nome in tutto il sito. *Evidenza A per WCAG 2.4.4, A/B per NN/g sui link specifici.*
- **Numeri**: ogni cifra in un title o in una meta è calcolata, non scritta a mano. Una cifra, un solo significato (oggi "indicatori" vale cinque cose).
- **Persona**: impersonale nelle schede e negli articoli, "tu" nelle pagine che chiedono un'azione, "noi" nelle pagine di fiducia. Il "tu" del quiz resta, è un sottomarchio dichiarato.
- **Quiz**: giudicato con la sua voce. È il testo migliore del sito. Non si porta verso la voce dell'atlante.

## 5. Difetti trovati, ordinati

**Errori veri (non opinioni):**

1. `Eta media della popolazione`, manca l'accento, in title e H1 di `ter-920` (270 impressioni). Viene dal dato (`external_indicator_manifest.csv:387`), non dal copy.
2. Title delle due classifiche qualità della vita: `Qualità regioni: Equilibrato | Divario Italia` (`v1/classifica.html:32`). Non contiene "classifica", il nome interno del profilo sta al posto della parola cercata, grammatica spezzata. Nessun test lo difende. Il concorrente diretto (Lab24) usa la forma esatta che gli utenti cercano.
3. Atlante: title di 73 caratteri e meta di 168, sopra i budget. Anche meta di home (157), province (158) e due articoli (159, 160).
4. `ter-104`: il title promette "Livello di istruzione" ma il dato è la quota con *al massimo* la licenza media, cioè il contrario di ciò che si aspetta chi cerca. La meta lo spiega, il title no.
5. Cinque grandezze chiamate "indicatori": 597 (catalogo), 372 (indicizzabili), 634 (universo editoriale, in `CLAUDE.md` e `STATUS.md`), 67 (serie con livello provinciale, mostrate come `Province 67` accanto a "107 province"), 158/142 (stessa regione, stessa schermata).
6. Etichette multiple per la stessa destinazione: `/confronto` ha tre nomi, `/qualita-della-vita` cinque, `/blog` tre, e `nav.py:33-34` scrive a mano `20` e `107`.
7. Il sottotitolo di `/confronto` mostra un tema a caso (`Cultura, patrimonio e turismo`) a chi arriva dalla SERP.
8. Meta troppo corte: `ter-281` (46 caratteri), `ter-921` (56), `ter-12` è una definizione senza territorio.
9. `/temi`: la meta nomina "trasporti", che non è fra i temi elencati. Da verificare.

**Da non trattare come difetti** (smentiti dall'audit): lo spazio in "7 ª" (artefatto dell'estrazione, nel DOM non c'è); gli H2 di menu e footer (struttura da valutare a parte, non copy).

## 6. Priorità, costo, rischio

| Pri. | Intervento | Costo | Rischio | Perché |
| --- | --- | --- | --- | --- |
| P0 | Title delle due classifiche qualità della vita | 1 template, nessun test lo cita | Basso | È il difetto più evidente, ha il concorrente più forte, e l'indice ha 721 impressioni a CTR 2,2% |
| P0 | Accento di `Eta media` | 1 riga di dato più un test | Basso, ma controllare che la pipeline non lo ripristini | Errore di ortografia visibile |
| P0 | Meta e title sopra budget (atlante, home, province, 2 articoli) | 3 template, 2 articoli in `content/` (via PR) | Basso, i test misurano già la lunghezza | Il taglio avviene a caso |
| P0 | Allineare title, H1 e og:title nei 16 articoli | `content/posts/*.md`, via PR | Basso, pagine con pochi clic | Riduce la riscrittura di Google |
| P1 | `Province 67` in home | 1 template | Medio, `test_home_atlante.py:96-98` | Il lettore legge 67 province |
| P1 | Numeri a mano in `nav.py` | 2 righe | Medio, `test_home_doors.py` | Resta vero solo finché i territori non cambiano |
| P1 | Meta brevi delle schede (`ter-12`, `ter-281`, `ter-921` e altre) | 1 PR per scheda, sono i lead in `content/indicators/` | Medio, test su lead e description | Non è stato contato quante siano sotto 110 caratteri |
| P1 | Title di `ter-104` (cosa misura davvero) | 1 scheda | Medio: è un nome ufficiale, scollega title e URL | Decisione editoriale |
| P1 | Un solo esperimento di CTR su `ter-901`, solo la meta, 3 settimane | 1 scheda | Il più misurabile | 4.258 impressioni, il 21% del traffico visibile |
| P2 | CTA vaghe (`Un altro indicatore`, `Tutta la scheda`, `Altro`) | 4 template, 2 test da aggiornare | Alto rispetto al guadagno | Si tocca un test per un'etichetta |
| P2 | Allineare le etichette di nav | `nav.py` | Basso | Nessun dato dice che il lettore si perda |
| P2 | 158 contro 142 nella regione | `views._region_title` e `regione.html:110` | Medio-alto, 3 test | Quale numero tenere è editoriale |

**Da non fare ancora:**
- Riscrivere in massa i title delle 388 schede. Non misurabile, 76 test sulla formula, e `docs/AUDIT_VOCE.md` dice già che variare costa.
- Toccare title di `ter-12` (CTR 7,9%, posizione 5,5), `ter-13`, `ter-281`: funzionano.
- Unificare la convenzione di marca nel title (oggi quattro): costa 10 template e rompe `test_app.py:1032`. Nessuna evidenza che aiuti il CTR. Decidere dopo un caso concreto.
- Cambiare più di una scheda alla volta: con 614 clic non si attribuisce l'effetto.
- Qualunque tocco a canonical, noindex, 301 delle URL legacy, schema dati.

## 7. Raccomandazione

Fare i quattro P0 in **una PR sola per il codice** (template e un dato) e **una per i contenuti** (articoli), perché sono piccoli, difesi poco dai test e correggono difetti non discutibili. Poi l'esperimento su `ter-901`, e solo dopo aver visto il risultato decidere su `ter-104`, marca e CTA.

Il guadagno SEO atteso dai soli testi è **basso o medio**. Il guadagno vero è di chiarezza e fiducia: un lettore che trova 597, 372 e 67 nello stesso sito si chiede quale sia giusto. Questo è il motivo per cui l'uniformità batte la creatività.

## 8. Che cosa non sappiamo

- **Query per pagina.** Le query che portano a ogni scheda non sono state estratte da Search Console. Il passo successivo, prima di decidere sui title delle schede, è questo. Con 614 clic resterà comunque un campione piccolo.
- **Quanti** title e meta di scheda sono sotto 110 o sopra 155 su 388: l'audit ha misurato un campione.
- **Quiz**: l'HTML è un guscio, ne abbiamo letto solo title, meta e H1 server-side. Il testo visibile, gli stati vuoti e gli errori non sono stati inventariati. Serve un inventario dopo un'interazione.
- **Studi su CTR**: tutti in inglese e quasi tutti USA, nessuno su siti di dati italiani.
- **La suite di test non è stata eseguita** da nessun worker: il costo dei test è stimato per ricerca di stringa.
- **Competitor**: pagine dietro login o JavaScript (ItaliaOggi, Lab24 H1) non lette. Nessuna stima del loro traffico.
- Il confronto tra scelte A/B di testo non si può decidere con i dati che abbiamo: lo studio dice cosa è più coerente, non cosa fa più clic.
