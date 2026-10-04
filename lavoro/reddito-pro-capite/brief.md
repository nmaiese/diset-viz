# Brief del pilota 1 del blog: reddito pro capite per regione e PIL

Scritto dal team leader il 4 ottobre 2026. È materiale, non una scaletta: le parti non hanno un ordine, non vanno usate tutte, e il pezzo non ha sezioni predefinite. È l'unico input numerico dello scrittore, oltre alle citazioni letterali di `fonti.md`.

## La domanda di chi cerca
Query vere (Search Console, 28 giorni al 1 ottobre 2026, e Semrush Italia): "reddito pro capite regioni italiane" (28 impressioni, posizione 7,3), "reddito pro capite per regione" (10, posizione 5,7), "reddito pro capite italia" (18, posizione 18,6, volume Semrush 1.300), "reddito medio pro capite italia" (volume 170). Chi scrive "reddito pro capite" nella ricerca, oggi, trova sul sito il PIL: il sito ha già un pezzo sul [PIL pro capite per regione](/blog/pil-pro-capite-regioni-divario-2024) e la scheda del PIL. Manca una risposta alla domanda "e il reddito?". Questo pezzo non deve ripetere quello sul PIL: non riscrivere la classifica del PIL.

## La tesi, in una frase
Il reddito delle famiglie e il PIL sono due mappe diverse dello stesso Paese: sul reddito la distanza fra Lombardia e Calabria è più bassa che sul PIL e si è accorciata dal 2004, sul PIL si è riaperta, e nel mezzo della classifica le regioni cambiano posto.

## Dati (dal sito, Istat Conti economici territoriali, edizione dicembre 2025, valori correnti, anno 2024)
Le due serie sono le schede [PIL pro capite](/indicatore/pil-pro-capite/ter-901) e [Reddito disponibile delle famiglie per abitante](/indicatore/reddito-disponibile-delle-famiglie-per-abitante/ter-902). Il dossier deterministico è in `dossier-ter-901.json` e `dossier-ter-902.json`, la tabella delle venti regioni in `app/static/data/articles/reddito-pro-capite-regioni.csv` (da creare nel ramo se manca: la ricalcola da `data.get_indicator`).

| Regione | PIL pro capite 2024 (euro) | Reddito disponibile delle famiglie per abitante 2024 (euro) | Reddito su 100 di PIL | Posto per PIL | Posto per reddito |
|---|---|---|---|---|---|
| Trentino Alto Adige | 54.637 | 29.344 | 54 | 1 | 1 |
| Lombardia | 50.399 | 28.154 | 56 | 2 | 2 |
| Valle d'Aosta | 47.743 | 25.751 | 54 | 3 | 4 |
| Emilia-Romagna | 44.557 | 26.684 | 60 | 4 | 3 |
| Lazio | 43.167 | 24.437 | 57 | 5 | 10 |
| Veneto | 41.496 | 24.652 | 59 | 6 | 8 |
| Toscana | 39.262 | 24.496 | 62 | 7 | 9 |
| Friuli-Venezia Giulia | 39.005 | 24.781 | 64 | 8 | 7 |
| Liguria | 38.842 | 25.504 | 66 | 9 | 5 |
| Piemonte | 38.626 | 25.426 | 66 | 10 | 6 |
| Marche | 34.149 | 22.489 | 66 | 11 | 12 |
| Umbria | 32.467 | 22.524 | 69 | 12 | 11 |
| Abruzzo | 32.109 | 20.310 | 63 | 13 | 13 |
| Basilicata | 28.416 | 17.816 | 63 | 14 | 17 |
| Sardegna | 27.731 | 19.870 | 72 | 15 | 14 |
| Molise | 27.698 | 18.662 | 67 | 16 | 15 |
| Campania | 24.564 | 17.177 | 70 | 17 | 19 |
| Puglia | 24.328 | 17.898 | 74 | 18 | 16 |
| Sicilia | 23.309 | 17.402 | 75 | 19 | 18 |
| Calabria | 21.702 | 16.796 | 77 | 20 | 20 |

Fatti verificati dal leader (ricalcolati dai dati, non arrotondare in modo diverso):
- Lombardia/Calabria nel 2024: PIL 50.399 e 21.702 euro, rapporto 2,32 (scrivere 2,3). Reddito 28.154 e 16.796, rapporto 1,68 (scrivere 1,7). Differenza di reddito: 11.358 euro per abitante.
- Nel 2004 gli stessi rapporti erano 2,19 sul PIL e 1,79 sul reddito. Prima e ultima regione di ogni classifica: PIL da 2,25 a 2,52, reddito da 1,80 a 1,75 (2004 contro 2024). I due rapporti si muovono quindi in direzioni opposte, e vale anche per la prima e l'ultima regione.
- Posti che cambiano fra le due classifiche: Lazio dal quinto posto per PIL al decimo per reddito, Liguria dal nono al quinto, Piemonte dal decimo al sesto, Veneto dal sesto all'ottavo, Toscana dal settimo al nono, Valle d'Aosta e Emilia-Romagna si scambiano il terzo e il quarto. Il Trentino-Alto Adige è primo e la Calabria ultima in entrambe. I posti cambiano per 16 regioni su 20 ma le due graduatorie sono vicine: la correlazione di rango (Spearman) è 0,93.
- Il reddito disponibile vale da 54 euro ogni 100 di PIL (Trentino-Alto Adige) a 77 (Calabria). Cinque valori più alti del rapporto: Calabria 77, Sicilia 75, Puglia 74, Sardegna 72, Campania 70. Il rapporto scende al salire del PIL (correlazione di rango -0,93, con eccezioni).
- Bolzano, da sola (aggregato Istat, non del sito): PIL 61,6 mila euro e reddito 32,7 mila nel 2024, prima su entrambe. Il sito usa il Trentino-Alto Adige come regione: dirlo se si nomina Bolzano (fonte: Istat, `fonti.md` 2a, tra le `external_figures`).
- Differenze fra regioni vicine si calcolano dai valori non arrotondati (il Veneto supera il Lazio di 216 euro sul reddito, non 215).

## Fonti ammesse per le definizioni e le cause (`fonti.md`)
Solo le citazioni letterali con URL aperto: definizione Istat di PIL (1a) e di reddito lordo disponibile (1b), dato 2024 (2a), calcolo in valori correnti (5a), l'audizione Istat del 28 maggio 2025 sulla redistribuzione (3a), Eurostat sulla differenza fra luogo di produzione e residenza (3b, 3c), Treccani (3d), Banca d'Italia 2010 (3e, solo come meccanismo generale), Svimez 2025 (3f, 4a). Le voci "non trovato" restano non trovate: il pezzo non dice quanto spieghi ciascun fattore in ogni regione, e non dice perché il Lazio scende. Il PIL è registrato dove si produce, il reddito dove vive la famiglia, e il reddito include imposte, contributi, prestazioni sociali e altri trasferimenti netti: dirlo con queste parole e senza di più.

## Cose da non scrivere
- Il rapporto reddito su PIL come "quota del PIL che arriva alle famiglie" (grandezze di natura diversa: residenza contro produzione): è un confronto, non un flusso. Usare "equivale a" o "vale".
- Nessuna causa regione per regione. Niente "probabilmente perché". Niente "il Sud", se non come lista di regioni nominate.
- Niente confronto nel tempo di livelli in euro correnti: solo rapporti fra regioni nello stesso anno, e il rapporto di due anni diversi come rapporti.
- Il 2024 è dato "preliminare" per l'Istat: una riga sola, non una premessa.
- Il 2025: esiste solo la crescita in volume per ripartizione (+0,5% nazionale), nessun livello pro capite né reddito delle famiglie: non entra, salvo una riga se serve.

## Lezioni dalla bozza di riferimento del leader (scartata, riviste da un altro modello)
Una prima bozza scritta dal leader senza pipeline ha preso queste correzioni: le definizioni vanno fedeli (lordo, famiglie consumatrici, prestazioni sociali, prezzi di mercato), "il quadro non cambia" era falso (tutti e due i rapporti cambiano), la correlazione "in generale" va misurata (qui 0,93 e -0,93), mancavano i link `/regione/<chiave>` alla prima menzione di una regione con un valore, tre frasi portavano il caveat agganciato con la virgola e dovevano spezzarsi, il numero era scritto due volte (immagine e cifra) in una frase, e c'erano costrutti paralleli ripetuti. Sono i difetti da non rifare.

## Forma
- Frontmatter come negli articoli esistenti (`content/posts/2026-09-29-casa-affitti-mercato.md`): title (keyword all'inizio, entro 60 caratteri se possibile), seo_title, slug `reddito-pro-capite-regioni-non-e-il-pil`, description di 150-160 caratteri, date 2026-10-05, tags, `indicator: 901`, `draft: true`, blocco `dataset` con il CSV, `external_figures` per ogni numero che non viene dal sito (Bolzano 61,6 e 32,7). Senza `author`: la firma la dà `config/identita.yaml`. Nessun nome di persona.
- Un modello di voce, uno solo: `content/esempi/lavoce-salari-sud.md` (apertura sul significato, un contrasto vivido, nessuna chiusa riassuntiva). Non mediare con altri.
- Lunghezza: quella che serve alla tesi, indicativamente 800-1.200 parole. Un ancoraggio concreto per il lettore: due regioni a confronto. Una sola digressione.
- Il pezzo prevede un grafico e un'immagine di apertura (ruolo grafico, dopo lo scrittore): lo scrittore lascia i marcatori di figura come negli altri articoli e dice nel `worker_done` quale grafico regge la tesi.

## La lista "non IA" (è anche la lista del revisore)
Parte da una domanda di chi cerca e da dati con fonte e anno. Un taglio e una tesi, esempi territoriali concreti, numeri verificati. Niente schema fisso a sezioni, niente apertura generica, niente chiusura riassuntiva ("In due righe", "In conclusione"). Niente formule da IA ("è importante notare", "in un mondo in cui", "panorama", "tessuto", "cruciale") e niente elenchi puntati superflui. Frasi di lunghezza varia, italiano naturale, un'idea per frase, il caveat prende la sua frase. Nessun nome del titolare. Regole tipografiche di `content/STYLE.md`: niente em-dash, en-dash, punto e virgola, puntini.
