# Attribuzione e provenienza

Questa skill e' **`scrittura-italiana`** di **hypnosdesign**, adottata in
Divario Italia sotto la licenza **Creative Commons Attribution-ShareAlike 4.0
International (CC BY-SA 4.0)**. Il testo integrale della licenza e' in
[`LICENSE`](LICENSE).

- **Opera originale:** `hypnosdesign/claude-skill-scrittura-italiana`
- **Versione:** 2.18.0 (dal frontmatter di `SKILL.md`)
- **Commit di origine:** `4987e09b98b0d833b961a0224743e2353d39d6b1`
- **Data di adozione:** 2026-08-01
- **Licenza:** CC BY-SA 4.0 (`SPDX: CC-BY-SA-4.0`)

## Che cosa e' stato copiato, e che cosa no

Copiato **byte per byte, senza modifiche** (share-alike, opera intatta):
`SKILL.md`, la cartella `references/` (nove file), `README.md`, `CHANGELOG.md`,
`LICENSE`. La suite di eval a monte (`evals/evals.json`, `evals/manifest.json`,
`evals/README.md`) e' copiata, sempre invariata, sotto
[`evals/scrittura-italiana/`](../../../evals/scrittura-italiana/) del progetto.

**Non** copiato, perche' fuori dallo scopo qui e pesante: `evals/results/` (i
run storici di riferimento, ~13 MB), il sito in `docs/`, gli asset `assets/`
(GIF dimostrative), i workflow `.github/`, gli script Node del runner
(`evals/*.mjs`: richiedono Node e il CLI `claude`, non girano nella suite Python
del progetto).

## Modifiche (come richiede la clausola BY-SA "indicate changes")

I file dell'opera originale elencati sopra **non sono stati modificati**. Il
lavoro derivato del progetto vive in file separati e chiaramente marcati:

- [`evals/scrittura-italiana/PRECEDENZA.md`](../../../evals/scrittura-italiana/PRECEDENZA.md):
  la regola di precedenza degli assoluti di progetto sulle raccomandazioni
  tipografiche della skill, e il cancello deterministico che ne discende.
- [`evals/scrittura-italiana/tic_count.py`](../../../evals/scrittura-italiana/tic_count.py):
  un contatore deterministico dei tic, il cui lessico e' **distillato** dai
  `references/` della skill (`stile-naturale.md`, `cliche-e-parole-alla-moda.md`).
  E' quindi anch'esso opera derivata sotto CC BY-SA 4.0.

Questi file derivati sono rilasciati sotto la stessa **CC BY-SA 4.0**, come la
share-alike impone.

## La precedenza, in una riga

La skill lavora in *testo controllato* e li' consiglia caporali `« »`, lineette
spaziate e punto e virgola. **Gli assoluti di Divario Italia li vietano.** In
caso di conflitto vincono sempre gli assoluti di progetto: niente `—`, `–`, `;`,
`…`, virgolette dritte. La regola completa e la sua ragione stanno in
[`content/STYLE.md`](../../../content/STYLE.md) e in `PRECEDENZA.md`.
