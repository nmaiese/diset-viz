---
name: modelli-societa
description: Scegli il modello giusto prima di lanciare un worker o una review (Codex, Claude, Antigravity, OpenCode, Ollama, Grok). Usala ogni volta che stai per usare orca-lancia, delegare un lavoro, fare una review di altra famiglia o decidere se un dato personale può andare a un modello.
---

# Modelli della società: scegli prima di lanciare

La fonte unica è `MODELLI.md` in questa cartella (copia di `dev-tools/docs/MODELLI.md`; se diverge, vale dev-tools). Leggila: ha i
comandi esatti, le peculiarità di ogni CLI, le quote e le tabelle 1ª/2ª scelta. Questa skill è solo il promemoria.

I percorsi `~/dev/dev-tools/...` esistono solo sulla workstation: una sessione cloud non lancia worker Orca, usa questa
skill solo per scegliere il modello e per la regola della review di altra famiglia.

## Prima di ogni lancio (4 domande, in ordine)

1. **Dati personali?** Sì → solo `claude haiku` (o `sonnet`). Mai Codex, mai gratuiti OpenCode, mai Antigravity
   individuale. No → continua.
2. **Che lavoro è?** Codice → Codex `gpt-6-luna`. Review di altra famiglia → Antigravity `gemini-3.1-pro-high` o
   OpenCode `longcat-2.5-preview-free`. Ricerca su dati pubblici → Antigravity `gemini-3.8-flash-high`. Lavori
   semplici, test, riepiloghi → OpenCode `longcat-2.5-preview-free`. Ragionamento difficile / red team →
   `gpt-6-astra`, **un solo giro**, con riga nel battito. (Tabella completa: MODELLI.md §7.)
3. **C'è quota?** Codex: massimo 2 vivi nella società (guarda i battiti), un solo lancio alla volta, demone
   `remote-control` spento. Gratuiti: `big-pickle` esaurito il 06/10, `nemotron-3-ultra-free` dà 503: se non risponde
   passa a `longcat`. OpenCode Go: quota esaurita il 06/10, reset non letto. Quote reali: «non letto» finché
   `limiti.json` è a mano.
4. **Review di altra famiglia:** l'autore non rivede se stesso. Autore Codex/Claude → Gemini o OpenCode; autore
   Gemini → Codex Luna. Mai catene di review Astra.

## Comando

```bash
~/dev/dev-tools/scripts/orca-lancia.sh --agent <codex|claude|opencode|antigravity|grok> \
  [--model <slug>] [--effort <low|medium|high|xhigh|max|ultra>] \
  --worktree <compito> --spec-file <file> [--sola-lettura] [--scrivi-trust]
```

- Nel battito scrivi il **modello esatto** e il mix per modello della giornata, non solo il provider.
- Antigravity: `--model` ed `--effort` non passano (il modello sta in `~/.gemini/antigravity-cli/settings.json`);
  primo lancio in un worktree nuovo con `--scrivi-trust`. OpenCode: `--effort` rifiutato.
- Mai `codex exec`, `claude -p`, `opencode run`, `agy -p`: una guardia li nega.
- Il titolo della scheda è «<progetto> · worker · <compito> · <agente>:<modello>».
- Un worker è concluso dopo `worker_done` letto con `orchestration check`; poi
  `scripts/orca-fine-worker.sh --worktree <percorso>`.

## Se il catalogo sembra cambiato

Rileggilo dalle CLI (comandi in MODELLI.md §9) e correggi MODELLI.md: i nomi dei modelli e le quote cambiano più
in fretta di questo promemoria.
