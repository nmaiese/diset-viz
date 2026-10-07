# Autore v3: chi eroga le cure fuori regione

Articolo: `content/posts/2026-10-07-chi-eroga-cure-fuori-regione.md`, slug `chi-eroga-cure-fuori-regione`, `draft: true`. Dati: `app/static/data/articles/chi-eroga-cure-fuori-regione.csv`. Brief: `brief.md` (SHA 4c3ebf48), Gate A v3 PASSA (2cdcdfd1). Unico input numerico: il brief. La v2.1 (`2026-10-07-medici-di-famiglia-regioni.md` e il suo CSV) è intatta e non riusata, ID TER del vecchio articolo non copiato.

## Claim table

| # | Frase nel testo | Fonte | Periodo | Unità | Trasformazione | Limite |
|---|---|---|---|---|---|---|
| 1 | Lombardia: privato 73,2% del valore dei ricoveri in mobilità | GIMBE, tab. 4.5, PDF p. 26 | 2023 | % del valore, ordinari e day hospital | nessuna | Mobilità attiva, valore non volumi, no filtro mobilità effettiva |
| 2 | Lombardia: 61,9% della specialistica | GIMBE, tab. 4.5 | 2023 | % del valore, specialistica ambulatoriale | nessuna | idem |
| 3 | Emilia-Romagna: 59,1% dei ricoveri | GIMBE, tab. 4.5 | 2023 | % del valore | nessuna | idem |
| 4 | Emilia-Romagna: 25,5% della specialistica | GIMBE, tab. 4.5 | 2023 | % del valore | nessuna | idem |
| 5 | Distanza 14,1 punti nei ricoveri | calcolo | 2023 | punti percentuali | 73,2 - 59,1, su valori a un decimale | Non causale, non differenza fra pazienti |
| 6 | Distanza 36,4 punti nella specialistica | calcolo | 2023 | punti percentuali | 61,9 - 25,5 | idem |
| 7 | 544.316 ricoveri di mobilità effettiva, circa 2,4 mld di euro | AGENAS, PDF p. 18 (stampata 17), scheda 15/04/2026 | 2024 | numero ricoveri, euro | nessuna | Ricoveri non pazienti unici. Coorte regioni-finanziata, esclusi casuale e apparente. Data è della scheda, il PDF non ha un giorno proprio |
| 8 | Privato accreditato 62,62% dei ricoveri e 69,23% della spesa | AGENAS, PDF p. 18 | 2024 | % ricoveri, % spesa | nessuna | Spesa tariffaria non è costo effettivo né profitto |
| 9 | "Prevale il privato" nei ricoveri della mobilità effettiva (nazionale) | AGENAS | 2024 | quote > 50% | confronto con 50% | Solo ricoveri, solo nazionale |
| 10 | Toscana: 34,0% ricoveri, 5,5% specialistica, passa soprattutto dal pubblico | GIMBE, tab. 4.5 | 2023 | % del valore | "soprattutto dal pubblico" = 100 meno quota privata, > 50% | Valore, non volumi. Controllo contrario |
| 11 | Emilia-Romagna: nella specialistica il privato è in minoranza, controesempio a "va sempre nel privato" | GIMBE | 2023 | % del valore | 25,5 < 50 | Valore, non pazienti. Frase retorica "chi si cura fuori regione va sempre nel privato" è del brief, non attribuita a nessuno |
| 12 | Prevale nel dato nazionale dei ricoveri e in Lombardia | AGENAS 2024, GIMBE 2023 | 2023, 2024 | % | confronto con 50% | Due anni e perimetri diversi, dichiarato nel testo |
| 13 | Lombardia 5,3% e Emilia-Romagna 5,7% ricoveri acuti ordinari dei residenti fuori regione | Istat, audizione LEA 07/07/2026 (pubb. 08/07), PDF p. 18; coincide con bes:12SER025 2024 | 2024 | % dei ricoveri dei residenti | nessuna | Descrive chi esce, non chi eroga |
| 14 | "Le due regioni, che sono anche poli di arrivo, vedono uscire pochi ricoveri" | Istat 2024 + GIMBE (polo di attrazione dal brief) | 2023-2024 | qualitativa | "pochi" = 5,3 e 5,7 contro Calabria 22,8 | Giudizio editoriale. Nessun volume di arrivo è citato. Anni diversi |
| 15 | Calabria 22,8%, senza destinazione | Istat | 2024 | % | nessuna | Non identifica dove vanno i calabresi. Solo contesto |
| 16 | Mobilità di confine può dipendere dalla comodità degli spostamenti | Ministero della Salute, Rapporto SDO 2024, PDF p. 34 (stampata 24) | giugno 2026 | qualitativa | parafrasi | Limite interpretativo, non misurato per i due territori. Giorno di pubblicazione non verificato, la fonte non è contata fra le tre |
| 17 | GIMBE 2023 e AGENAS 2024 non misurano una variazione e hanno perimetri diversi | brief, passo 2 e "Serie esterna" | 2023, 2024 | nota | nessuna | Quota AGENAS non va nelle barre |

## Scelte editoriali

- **Titolo**: "Cure fuori regione: chi le fa in Lombardia ed Emilia-Romagna" (59 caratteri), nessun termine tecnico. L'apertura ripete il contrasto con cifre e anno. "Valore" compare nel lead come "valore dei ricoveri", senza "mobilità attiva", che non è usata nel corpo.
- Il privato è chiamato "privato accreditato" con AGENAS e "privato convenzionato" con GIMBE, come nelle fonti. Non ho affermato che siano la stessa categoria.
- Toscana come controllo contrario in sezione propria, Calabria solo come contesto sull'uscita dei residenti, come da brief.
- `bes:12SER025` è base nella sezione "Chi parte non è chi cura", non tesi. Link canonico `/indicatore/emigrazione-ospedaliera-in-altra-regione/bes-12SER025`, controllato dalla guardia (200). Link al vecchio pezzo `/blog/emigrazione-ospedaliera-mobilita-sanitaria-regioni` come prossimo passo, come indicato nel brief.
- Nessuna persona, nessun riassunto finale, chiusura su link concreti e CSV. Niente cause, qualità, spesa diretta, doppi incarichi, traiettorie.
- Il CSV ha formato lungo (misura, unità, anno, territorio, valore, fonte, note) con le sei celle GIMBE, le due quote AGENAS, le tre Istat, il numero ricoveri AGENAS e le due differenze calcolate. Valore "circa 2,4 miliardi" è solo in `external_figures`, non nel CSV.
- `external_figures` elenca tutti i valori esterni nel testo con URL e data della fonte. Il dettaglio sulle date: AGENAS scheda 15/04/2026, GIMBE 04/03/2026, Istat 08/07/2026.
- Frontmatter: `indicator: bes-12SER025`, nessun `author`, nessuna `cover`.

## Controlli

- Guardia: 757 parole (tetto 1100), 0 avvisi, 0 non verificabili, link interni tutti 200. **1 errore residuo atteso**: manca lo SVG della figura `erogatori-cure-fuori-regione`. Non va chiamato verde: la guardia non è chiusa finché il grafico non esiste.
- `git diff --check` pulito sui miei file (l'avviso CRLF riguarda `data/derived/casa_titolo_godimento.csv`, non mio, non toccato).
- Ricerca dei caratteri vietati `[—–;…]` sull'articolo: nessuna corrispondenza.
- La guardia non segnala la copertina assente: `cover` volutamente non impostata, `cover_alt` e `cover_credit` da aggiungere con la foto.

## Resta da fare

1. **Grafico**: barre orizzontali affiancate, 6 barre (ricoveri e specialistica per Lombardia, Emilia-Romagna, Toscana), scala 0-100, anno 2023 vicino al titolo, nota fonte GIMBE e limite visibili. Percorso atteso `<figures>/chi-eroga-cure-fuori-regione/erogatori-cure-fuori-regione.svg` con `<title>` e `<desc>`. Sorgente celle: il CSV. Non aggiungere la quota AGENAS.
2. **Copertina**: foto con licenza libera e `cover`, `cover_alt`, `cover_credit` (autore, licenza, fonte).
3. Bozza HTML e Gate B in revisione. Revisione dello stile da altra famiglia di modelli.
4. Il brief indica il PDF AGENAS senza giorno proprio: la data 2026-04-15 è della scheda.
