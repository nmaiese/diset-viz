Pilota del team editoriale (`docs/design_drafts/team/PIANO.md`, fase 3). La scheda da riscrivere è `/indicatore/tasso-di-disoccupazione/ter-12`.

### Intent
La disoccupazione è scesa in ogni ripartizione dal 2018 al 2025. Perché nel Mezzogiorno resta più del doppio che al Nord, che cosa la muove, e che cosa cambia fra donne e uomini?

### Che cosa misura, in una riga
Su cento persone che lavorano o cercano lavoro, quante lo stanno cercando senza averlo trovato. **Nello, rileggi questa riga: è la base del brief dello scrittore.**

### Dati e fonti
- Dataset: Istat, catalogo territoriale (ter-12), con le dimensioni per sesso in ter-175 (maschi) e ter-176 (femmine)
- Periodo: 2018-2025
- Territorio: 20 regioni
- Fonti esterne ammesse: quelle verificate dallo scout in `lavoro/ter-12/fonti.md`, con l'URL aperto e la citazione letterale

### Output posseduti
- Testo: `content/indicators/12.md`, in forma libera
- Grafica: un marcatore `<!-- grafico: dispersione con=ter-901 ... -->` dentro l'articolo, se il testo lo richiama
- Materiale: `lavoro/ter-12/dossier.json`, `fonti.md`, `brief.md`

### Accettazione
- [ ] cifre riproducibili dal dossier o dalle citazioni di `fonti.md`, con la guardia verde
- [ ] fonti in `fonti.md` verificate, con l'URL aperto e la citazione letterale
- [ ] test del repository verdi
- [ ] verdetto del revisore Orca `PRONTA PER NELLO`
- [ ] giudizio di Nello prima del merge

### Chi fa che cosa
Il 28 settembre sera Nello ha chiesto di accelerare con i provider rimasti, senza Claude e senza Codex. I ruoli girano in headless, lanciati dal team leader, con `timeout` e `< /dev/null` (quote misurate in `docs/WORKFLOW_ORCA.md` §6).
- **Scout**: Antigravity gemini-3.1-pro-high. Il giro web parallelo lo fa OpenCode nemotron-3-ultra-free. Il team leader verifica le citazioni aprendo gli URL.
- **Scrittore**: Antigravity gemini-3.1-pro-high.
- **Grafico**: OpenCode big-pickle.
- **Revisore**: OpenCode big-pickle in una sessione nuova, di famiglia diversa dallo scrittore, con il secondo parere di ollama-cloud gpt-oss:120b.
- **Lettura cieca**: gpt-oss:120b e gemma4:31b.

## Stato
Run: headless, nessun run Orca
Fase: scout in corsa (fonti per le sei voci)
SHA: nessuno
Prossimo passo: le review 2 di #289 e #290, poi l'allineamento della pila e il worktree `ind-ter-12` dalla cima. Lo scout intanto lavora fuori dal worktree, e i suoi file entrano in `lavoro/ter-12/` quando il worktree c'è.
Chi lo fa: team leader
