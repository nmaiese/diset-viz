---
name: modelli-societa
description: "Sceglie modello e famiglia per coordinamento, worker, review e dati personali. Usala prima di assegnare lavoro o scegliere revisore."
---

# Modelli della società

Fonte unica: `~/dev/dev-tools/docs/MODELLI.md`; rileggi §7 e Regolamento prima di assegnare. Quote non lette restano «non letto».

## Quattro domande

1. Il lavoro tratta dati personali? Se sì, solo Claude Haiku o Sonnet; mai Codex, agy individuale o modelli gratuiti.
2. È codice, analisi, ricerca, documentazione o red team? Usa tabella e §7.
3. Chi autore e revisore? Revisore sempre famiglia diversa.
4. Mix giornaliero vicino 40% per provider? Nessun tetto ai Codex vivi; il limite del 40% circa vale per provider.

| Lavoro | Scelta / revisore |
|---|---|
| Codice ordinario | Codex GPT-6 Luna; Sol per codice impegnativo |
| Documenti lunghi o coordinamento | Codex GPT-6 Sol oppure Claude Sonnet secondo alternanza coordinatori |
| Dati personali | Claude Haiku per lavoro semplice; Sonnet per coordinamento o lavoro impegnativo |
| Review: autore Claude o Codex | Antigravity Gemini 3.1 Pro High; alternativa OpenCode LongCat gratuito |
| Review: autore Gemini | Codex GPT-6 Luna |
| Ricerca su dati pubblici | Antigravity Gemini 3.8 Flash High; alternativa OpenCode LongCat gratuito |
| Test | OpenCode LongCat gratuito; alternativa Codex GPT-6 Luna low |
| Riepiloghi e compiti meccanici | OpenCode LongCat gratuito; alternativa Claude Haiku |
| Decisioni difficili dei coordinatori o direzione | Codex GPT-6 Astra o Claude Opus; per direzione, Opus solo per decisioni difficili |
| Red team a contesto pulito | Codex GPT-6 Astra, un giro; alternativa Antigravity Gemini 3.1 Pro High |
| Review | Famiglia diversa da autore; non basta cambiare modello nello stesso provider |

Coordinatori alternano Claude Sonnet ↔ Codex GPT-6 Sol: mai Luna o Haiku. Mix provider circa 40%; nessun provider inattivo. Astra solo un giro, mai in catena di review. Non inferire quote non lette.

## Lancio

```bash
~/dev/dev-tools/scripts/orca-lancia.sh --agent <codex|claude|opencode|antigravity|grok> \
  [--model <slug>] [--effort <livello>] --worktree <compito> --spec-file <file>
~/dev/dev-tools/scripts/orca-lancia.sh --attivita <nome> --worktree <compito> --spec-file <file>
```

`--attivita` prende modello da `agents/ruoli.tsv`; non combinarlo con `--model`. `--model` è opzionale; agy non seleziona modello dal launcher e rifiuta `--effort` (modello ed effort nelle impostazioni Antigravity). Anche OpenCode rifiuta `--effort`. Mai headless. I modelli gratuiti ricevono dati personali: nessuno.

## Rilettura catalogo

```bash
codex debug models
agy models
opencode models
grok models
claude --help
```

Catalogo e quote cambiano; non dichiararli verificati senza lettura odierna.
