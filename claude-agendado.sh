#!/usr/bin/env bash
# claude-agendado.sh — Dispara Claude Code num horário específico
# Uso: ./claude-agendado.sh 23:00
# Sai quando Claude encerrar (matar com Ctrl+C interrompe o sleep)

set -e

TARGET_TIME="${1:?Uso: $0 HH:MM   (ex: 23:00, 02:30)}"
SESSION_NAME="Rework geral e balanceamento"
PROMPT="/compact - Comprima o contexto para economizar tokens. Depois continue de onde parou e prossiga com o trabalho, de uma relembrada rapida no plano olhando @CURRENT_PLAN.md"
EFFORT="xhigh"
ALLOWED_TOOLS="Bash,Read,Write,Edit,Glob,Grep"
LOGFILE="claude-agendado.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"; }

# Validar formato HH:MM
[[ "$TARGET_TIME" =~ ^([01][0-9]|2[0-3]):([0-5][0-9])$ ]] || {
  echo "Erro: formato invalido. Use HH:MM (ex: 23:00, 02:30)"
  exit 1
}

# Calcular segundos até o horário alvo
now=$(date +%s)
target=$(date -d "$TARGET_TIME" +%s 2>/dev/null)
[ "$target" -le "$now" ] && target=$(date -d "tomorrow $TARGET_TIME" +%s)
sleep_sec=$(( target - now ))

log "Agendado para $TARGET_TIME (faltam $((sleep_sec / 3600))h $(((sleep_sec % 3600) / 60))m)"
printf "\rAguardando... (Ctrl+C para cancelar)\n"

sleep "$sleep_sec"

log "Horario alcançado. Retomando sessao '$SESSION_NAME'..."
claude -r "$SESSION_NAME" -p "$PROMPT" --effort "$EFFORT" --dangerously-skip-permissions --allowedTools "$ALLOWED_TOOLS"
EXIT=$?

log "Claude Code encerrou (exit code: $EXIT)"
