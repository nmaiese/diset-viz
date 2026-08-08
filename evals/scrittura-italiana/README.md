# Eval e metro della skill scrittura-italiana

Materiale a valle della skill `scrittura-italiana`
([`.claude/skills/scrittura-italiana/`](../../.claude/skills/scrittura-italiana/)),
messo qui accanto a [`docs/WRITING_RUBRIC.md`](../../docs/WRITING_RUBRIC.md)
perché misura la stessa cosa: la qualità della prosa, come numero.

| file | che cos'è | origine |
|---|---|---|
| `evals.json`, `manifest.json` | i 46 casi di eval della skill (prompt + attese, giudizio LLM) | upstream, **invariati** (CC BY-SA 4.0) |
| `README-upstream.md` | come gira il runner Node della skill | upstream, invariato |
| `PRECEDENZA.md` | la precedenza degli assoluti di progetto + il cancello deterministico | progetto |
| `tic_count.py` | il contatore deterministico dei tic dell'italiano generato | progetto (lessico distillato dalla skill) |

**Da dove partire:** `PRECEDENZA.md` spiega perché i 46 casi non si toccano e
come il progetto ci mette sopra un cancello. `tic_count.py --self-test` prova il
metro sul metro.

Attribuzione, licenza e commit di origine:
[`.claude/skills/scrittura-italiana/ATTRIBUZIONE.md`](../../.claude/skills/scrittura-italiana/ATTRIBUZIONE.md).
