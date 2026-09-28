Sei lo scrittore del team editoriale di Divario Italia, nella riparazione 2 e ultima della PR #293 (scheda ter-12), lanciato dal team leader in headless. Lavori nel worktree corrente, commit 18c20f2a. Rileggi "In una riparazione" in skills/editorial-team/scrittore/SKILL.md.

Nella riparazione di prima un rilievo è stato saltato senza dirlo. Questa volta applica TUTTE e sei le correzioni qui sotto, in content/indicators/12.md, e nella risposta finale riporta per ciascuna la frase prima e la frase dopo. Se una non la applichi, dillo e spiega perché.

1. Sostituisci "Chi parte non cerca più lavoro al Sud e abbassa il tasso meridionale." con "Chi parte può quindi non cercare più lavoro al Sud e abbassare il tasso meridionale."
2. Togli la prima frase del corpo della prima sezione, "Il tasso di disoccupazione conta quante persone cercano lavoro senza trovarlo su cento individui in età 15 anni e oltre che lavorano o cercano." Il corpo comincia allora da "Chi non lavora e non cerca non entra nel conto." Se serve per la scorrevolezza, puoi portare nel primo paragrafo la forma "su cento persone che lavorano o cercano lavoro, quante lo stanno cercando senza averlo trovato", ma la definizione deve comparire una volta sola.
3. Togli dalla sezione "Il divario tra le ripartizioni non si è chiuso" la frase "Fra il 2018 e il 2025 il tasso di disoccupazione scende in tutte e venti le regioni.", che ripete l'attacco. Scrivi anche "passando dall'11,0% al 6,2% del 2025" al posto di "passando dall'11,0% a 6,2% nel 2025".
4. Nella frase sull'Istat 2024 metti il confronto che la fonte fa: "Secondo l'istituto, rispetto ai disoccupati, queste persone "si caratterizzano per una maggiore presenza di donne, di individui in classe di età più adulta, e di residenti nelle regioni del Mezzogiorno"."
5. La citazione sull'Istat 2024 con 26,7, 48,0 e 77,8 deve essere letterale, parola per parola come in lavoro/ter-12/fonti.md. La fonte dice "...e ben il 77,8 per cento tra le forze di lavoro potenziali che non hanno mai lavorato". Chiudi le virgolette dove vuoi, ma dentro le virgolette ci sono solo parole della fonte, nell'ordine della fonte.
6. Riscrivi "La regione è migliorata: occupazione e partecipazione crescono, pur chiarendo che "entrambi gli indicatori rimangono tuttavia su livelli significativamente inferiori alla media nazionale"." in modo che a chiarire sia la Banca d'Italia e non la regione, per esempio: "Occupazione e partecipazione crescono, ma la Banca d'Italia avverte che "entrambi gli indicatori rimangono tuttavia su livelli significativamente inferiori alla media nazionale"."

Non cambiare altro. Il marcatore <!-- grafico: ... --> resta dov'è. Niente em-dash, en-dash, punto e virgola, puntini di sospensione.

Controlli, tutti con uscita 0:
- DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py scripts/indicator_store.py --show ter-12
- DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia ter-12 --dossier lavoro/ter-12/dossier.json --fonti lavoro/ter-12/fonti.md
- git diff --check

Tocchi solo content/indicators/12.md. Nessun altro file nel worktree: niente rewrite.py, patch_*.py o report.md nella radice. I temporanei in /tmp, poi cancellati. Non fare git add né commit.
