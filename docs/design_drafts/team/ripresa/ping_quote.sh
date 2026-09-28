#!/usr/bin/env bash
# Ping di un messaggio per modello: dice chi risponde e chi e' senza quota.
S=/tmp/claude-1000/-home-nilo-dev-sites-divarioitalia--orca-worktrees-divarioitalia-orca-team-test/9ca29b59-2e0f-4c69-a1e4-2df8fa93451b/scratchpad
OUT=$S/ping
mkdir -p "$OUT"
cd "$S" || exit 1
MSG="Rispondi soltanto con la parola OK."

ping_oc() {
  local m=$1 f=$OUT/$(echo "$1" | tr '/:' '__').txt
  local t0=$(date +%s)
  timeout 120 opencode run "$MSG" -m "$m" < /dev/null > "$f" 2>&1
  local rc=$? t1=$(date +%s)
  printf '%-40s rc=%-3s %3ss  %s\n' "$m" "$rc" "$((t1-t0))" "$(grep -v '^\s*$' "$f" | tail -1 | cut -c1-90)"
}

ping_agy() {
  local m=$1 f=$OUT/agy_$1.txt
  local t0=$(date +%s)
  timeout 120 agy --model "$m" -p "$MSG" --print-timeout 110s < /dev/null > "$f" 2>&1
  local rc=$? t1=$(date +%s)
  printf '%-40s rc=%-3s %3ss  %s\n' "agy:$m" "$rc" "$((t1-t0))" "$(grep -v '^\s*$' "$f" | tail -1 | cut -c1-90)"
}

# Provider diversi in parallelo, ollama-cloud in fila (una richiesta alla volta).
{
  ping_oc opencode/big-pickle &
  ping_oc google/gemini-3.1-pro-preview &
  ping_oc zai/glm-5.3 &
  ping_oc moonshotai/kimi-k3 &
  ping_oc minimax/MiniMax-M3 &
  ping_oc groq/openai/gpt-oss-120b &
  wait
  ping_oc opencode/nemotron-3-ultra-free &
  ping_oc google/gemini-3.8-flash &
  ping_agy gemini-3.1-pro-high &
  ping_agy gemini-3.8-flash-high &
  wait
} &
{
  for m in kimi-k3 deepseek-v4-pro glm-5.3 qwen3.5:397b gpt-oss:120b; do
    ping_oc ollama-cloud/$m
  done
} &
wait
