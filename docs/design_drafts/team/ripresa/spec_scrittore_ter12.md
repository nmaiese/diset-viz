Sei lo scrittore del team editoriale di Divario Italia (issue #292 di nmaiese/diset-viz), lanciato dal team leader in headless. Oggi è il 28 settembre 2026. Lavori nel worktree corrente.

Prima di tutto leggi per intero skills/editorial-team/scrittore/SKILL.md: è il tuo unico contratto. Seguilo alla lettera, compreso l'ordine di lettura: lavoro/ter-12/brief.md, lavoro/ter-12/fonti.md, un solo modello di registro (content/esempi/lavoce-salari-sud.md, come dice il brief), le parti indicate di content/STYLE.md e di docs/INDICATOR_PAGES.md, content/indicators/901.md come esempio di frontmatter e di forma libera, il testo di oggi della scheda (per non ripeterlo).

Il compito: riscrivi content/indicators/12.md, la scheda del tasso di disoccupazione (/indicatore/tasso-di-disoccupazione/ter-12), in forma libera. È una pagina ad alto traffico: chi arriva ha cercato "disoccupazione regioni" e deve uscire sapendo che cosa misura il numero, com'è distribuito, come è cambiato dal 2018, e soprattutto perché il Mezzogiorno resta più del doppio del Nord. Italiano discorsivo, frasi corte, una idea per frase, il numero dentro la frase che lo spiega.

Vincoli che non si piegano:
- Le cifre sono SOLO quelle del brief e delle citazioni di fonti.md, scritte come sono scritte lì. Non fai differenze, rapporti, medie o somme. "Più del doppio" in parole va bene.
- Le cause vengono solo da fonti.md, con l'istituzione nominata nella frase e il link all'URL. Ogni URL citato va anche nel frontmatter fonti: con testo e url.
- La media semplice delle regioni non si chiama media nazionale.
- Niente em-dash, niente en-dash, niente punto e virgola, niente puntini di sospensione, neanche dentro una citazione (se una citazione ha un punto e virgola, ne citi solo una parte).
- Titoli di sezione che sono affermazioni, mai etichette. Nessuna sezione di cautele.
- Link agli indicatori canonici, come nel brief.

Controlli prima di finire:
- DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py scripts/indicator_store.py --show ter-12 esce con 0.
- DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia ter-12 --dossier lavoro/ter-12/dossier.json --fonti lavoro/ter-12/fonti.md esce con 0. Se segnala una cifra, correggi il testo (usa la cifra com'è nel brief o togli la frase), non aggirare la guardia.

Regole di lavoro: tocchi solo content/indicators/12.md. Non creare altri file nel worktree, niente script di lavoro (patch_*.py, report.md) nella radice: se ti serve un file temporaneo usa /tmp e cancellalo. Non fare git add né commit.

La tua risposta finale è un resoconto in italiano: il numero di parole, i titoli delle sezioni, ogni cifra usata con la sua provenienza (riga del brief o riga di fonti.md), e l'output della guardia.
