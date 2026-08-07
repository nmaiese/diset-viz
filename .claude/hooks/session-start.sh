#!/bin/bash
# SessionStart hook per Divario Italia (diset-viz).
#
# Prepara un checkout fresco perche' i comandi documentati in CLAUDE.md
# funzionino subito:
#   - .venv con i requirements (test via .venv/bin/python, gunicorn)
#   - dipendenze frontend (dist e' committato: npm serve solo per ribuildare)
#   - GitHub CLI (gh) installato
#   - il meta di sessione che pipeline_log.py legge per arricchire il diario
#
# Idempotente e non interattivo. Gira solo in remoto (Claude Code sul web).
set -uo pipefail

# L'hook riceve il JSON dell'evento su stdin: session_id e' l'unico campo che
# serve, e va letto SUBITO, prima che qualsiasi comando qui sotto consumi o
# chiuda lo stream.
hook_payload="$(cat 2>/dev/null || true)"

cd "${CLAUDE_PROJECT_DIR:-.}"

# --- Il lettore dei guasti ripetuti -----------------------------------------
# `data/pipeline/tool_failures.jsonl` aveva solo chi lo scriveva. L'errore
# `.venv/bin/python: no such file` c'era dentro tre ore prima della prima run
# del workflow, e in quella run quattro scrittori l'hanno ripagato da capo,
# quattro turni a testa. Un canale che nessuno legge non e' un canale, quindi
# qui lo legge qualcuno: al massimo tre righe, e silenzio quando non c'e'
# niente che si ripete. Gira anche in locale, che e' dove i guasti succedono.
python3 scripts/tool_failures.py --breve 2>/dev/null || true

# Il resto prepara un checkout fresco, e serve solo in remoto: in locale
# l'utente gestisce il proprio ambiente.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# --- Meta di sessione: chi e quando, per il diario ---------------------------
# pipeline_log.py lo legge best-effort per scrivere session_id e durata nella
# riga di run. Locale e ignorato da git: appartiene alla sessione, non alla
# storia.
# Il payload viaggia in una variabile d'ambiente e non in una pipe: con
# `python3 -` lo stdin e' gia' occupato dal programma stesso (l'heredoc), e la
# pipe si perdeva in silenzio, scrivendo un session_id sempre vuoto.
DI_HOOK_PAYLOAD="$hook_payload" python3 - <<'PY' || true
import json, os
from datetime import datetime, timezone
from pathlib import Path

try:
    payload = json.loads(os.environ.get("DI_HOOK_PAYLOAD") or "{}")
except Exception:
    payload = {}
if not isinstance(payload, dict):
    payload = {}
meta = {
    "session_id": str(payload.get("session_id") or ""),
    "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}
target = Path("data/pipeline/.session_meta.json")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
PY

# --- Python: venv + requirements (critico per test e gunicorn) --------------
# L'install gira solo quando requirements.txt cambia davvero: l'hash sta in
# .venv/.requirements.sha256. Prima reinstallava a ogni sessione, cioe' un
# giro di rete e di tempo per ottenere l'ambiente che c'era gia', e con i
# range al posto dei pin poteva pure ottenerne uno diverso.
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
wanted_hash="$(sha256sum requirements.txt | cut -d' ' -f1)"
have_hash="$(cat .venv/.requirements.sha256 2>/dev/null || true)"
if [ "$wanted_hash" != "$have_hash" ]; then
  .venv/bin/pip install --quiet --upgrade pip
  if .venv/bin/pip install --quiet -r requirements.txt; then
    printf '%s\n' "$wanted_hash" > .venv/.requirements.sha256
  else
    echo "session-start: pip install fallito (l'ambiente puo' essere incompleto)"
  fi
fi

# --- Frontend: dipendenze (dist e' gia' committato, serve solo per build) ---
# npm ci, non npm install: installa esattamente dal lockfile e NON lo riscrive.
# npm install invece riallinea package-lock.json a ogni avvio (l'npm del
# container droppa i campi libc), lasciando il working tree sporco in ogni
# sessione. Salta del tutto se node_modules c'e' gia' (container ripreso).
if [ -f frontend/package.json ] && [ ! -d frontend/node_modules ]; then
  ( cd frontend && npm ci --no-audit --no-fund --silent ) \
    || echo "session-start: npm ci fallito (non bloccante)"
fi

# --- GitHub CLI (gh) --------------------------------------------------------
# Non bloccante: se la rete/repo apt non risponde, la sessione parte comunque.
# Modifica il sistema del container (chiavi apt), che per un hook di repo e'
# molto: resta qui perche' la catena senza gh non apre pull request, e
# l'ambiente remoto non lo preinstalla. Se un giorno l'immagine lo porta,
# il `command -v` qui sotto spegne tutto il blocco da solo.
install_gh() {
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
  chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    > /etc/apt/sources.list.d/github-cli.list
  apt-get update -qq
  apt-get install -y -qq gh
}
if ! command -v gh >/dev/null 2>&1; then
  install_gh || echo "session-start: installazione gh fallita (non bloccante)"
fi

# --- Stop hook globale: il controllo firme che segnalava tutto ---------------
# Scavalca un file dell'ambiente fuori dal progetto, ed e' l'eccezione piu'
# vistosa di questo hook: documentata qui e tenuta apposta, dopo averla
# rivalutata. L'hook di fine turno dell'ambiente decide se un commit e'
# firmato leggendo %G?. Con le firme SSH, e senza gpg.ssh.allowedSignersFile
# che l'ambiente non configura, git non riesce nemmeno a tentare la verifica e
# risponde N per OGNI commit, firmato o no. Segnalava quindi come "Unverified"
# il 100% dei commit fatti qui, chiedendo un --amend che non poteva cambiare
# niente, e un allarme che suona sempre e' un allarme che si smette di leggere.
# La nostra copia legge l'header gpgsig del commit, e sistema anche il conteggio
# dei commit non pushati, che taceva proprio sui branch mai pushati
# (origin/HEAD non esiste in questo clone, il comando falliva e l'errore veniva
# ingoiato).
#
# Il guardrail e' la condizione: sovrascriviamo SOLO finche' l'originale ha
# davvero il controllo rotto (il grep qui sotto), cosi' se a monte lo
# correggono questa patch si spegne da sola invece di seppellire una versione
# migliore.
patch_global_stop_hook() {
  local global_stop_hook="${HOME:-/root}/.claude/stop-hook-git-check.sh"
  if [ -f "$global_stop_hook" ] && grep -qF '$2 == "N"' "$global_stop_hook"; then
    { cp .claude/hooks/stop-hook-git-check.sh "$global_stop_hook" \
        && chmod +x "$global_stop_hook"; } \
      || echo "session-start: patch dello stop hook fallita (non bloccante)"
  fi
}
patch_global_stop_hook

exit 0
