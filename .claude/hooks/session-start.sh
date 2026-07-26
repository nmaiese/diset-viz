#!/bin/bash
# SessionStart hook per Divario Italia (diset-viz).
#
# Prepara un checkout fresco perche' i comandi documentati in CLAUDE.md
# funzionino subito:
#   - .venv con i requirements (test via .venv/bin/python, gunicorn)
#   - dipendenze frontend (dist e' committato: npm serve solo per ribuildare)
#   - GitHub CLI (gh) installato
#
# Idempotente e non interattivo. Gira solo in remoto (Claude Code sul web).
set -uo pipefail

# Solo nell'ambiente remoto: in locale l'utente gestisce il proprio setup.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# --- Python: venv + requirements (critico per test e gunicorn) --------------
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

# --- Frontend: dipendenze (dist e' gia' committato, serve solo per build) ---
if [ -f frontend/package.json ]; then
  ( cd frontend && npm install --no-audit --no-fund --silent ) \
    || echo "session-start: npm install fallito (non bloccante)"
fi

# --- GitHub CLI (gh) --------------------------------------------------------
# Non bloccante: se la rete/repo apt non risponde, la sessione parte comunque.
if ! command -v gh >/dev/null 2>&1; then
  {
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
    chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list
    apt-get update -qq
    apt-get install -y -qq gh
  } || echo "session-start: installazione gh fallita (non bloccante)"
fi

exit 0
