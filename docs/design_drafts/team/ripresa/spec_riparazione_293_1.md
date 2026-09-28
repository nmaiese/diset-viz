Sei lo scrittore del team editoriale di Divario Italia, in una riparazione (PR #293, issue #292 di nmaiese/diset-viz), lanciato dal team leader in headless. Lavori nel worktree corrente, sul ramo della PR, commit 143c0db4.

Prima rileggi skills/editorial-team/scrittore/SKILL.md, in particolare "In una riparazione". Poi leggi la review 1 con gh pr view 293 --json reviews --jq '.reviews[-1].body', compresa la nota del team leader in fondo. Poi lavoro/ter-12/brief.md e lavoro/ter-12/fonti.md.

Correggi content/indicators/12.md su ogni rilievo:
- tutti i "no" delle domande 2, 3 e 4, con la correzione proposta o una migliore che dica la stessa cosa;
- la nota del team leader: la seconda sezione e metà della terza non devono più mettere in fila le cifre. Riscrivile come spiegazione. Tieni solo le cifre che servono al ragionamento (per esempio i livelli delle ripartizioni nel 2018 e nel 2025, e una o due regioni che mostrano il movimento), e lascia le altre al cruscotto della pagina, che mostra già serie, mappa e classifica. Una classifica si spiega, non si legge ad alta voce;
- le Note che la nota del team leader richiama: niente segno doppio ("un calo di 4,8 punti", non "di -4,8"), il titolo dell'ultima sezione parla di disoccupazione e non di disoccupati che "crescono", l'attacco non dice che "per uscirne basta smettere di cercare", niente "Esse fotografano solo".

L'attacco deve dire, in una o due frasi, che cosa misura il numero e qual è la notizia: la disoccupazione è scesa in tutte e venti le regioni dal 2018 al 2025, e il Mezzogiorno resta più del doppio del Nord. È anche la description in SERP.

Vincoli che restano: le cifre solo dal brief e dalle citazioni di fonti.md, scritte come lì, senza calcoli nuovi. Le cause solo da fonti.md, con l'istituzione nella frase e il link. Niente em-dash, en-dash, punto e virgola, puntini di sospensione, neanche dentro una citazione. Titoli che sono affermazioni. Il marcatore <!-- grafico: ... --> resta com'è, subito dopo il paragrafo che dice in parole che dove il reddito è più basso la disoccupazione è più alta: se riscrivi quel paragrafo, il marcatore resta subito sotto.

Controlli prima di finire, tutti con uscita 0:
- DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py scripts/indicator_store.py --show ter-12
- DIVARIO_PYTHON=/home/nilo/dev/sites/divarioitalia/.venv/bin/python bin/py -m scripts.editoriale.guardia ter-12 --dossier lavoro/ter-12/dossier.json --fonti lavoro/ter-12/fonti.md
- git diff --check (niente spazi in coda di riga).

Tocchi solo content/indicators/12.md. Nessun altro file nel worktree, niente script di lavoro nella radice, temporanei in /tmp e poi cancellati. Non fare git add né commit.

La tua risposta finale, in italiano: rilievo per rilievo che cosa hai cambiato (la frase prima e la frase dopo), il numero di parole, i titoli delle sezioni, e l'output dei tre controlli.
