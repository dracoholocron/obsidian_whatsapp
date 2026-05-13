#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$HOME/.openclaw/workspace"
CHECK_SCRIPT="$BASE_DIR/scripts/whatsapp-group-healthcheck.sh"
LOG_DIR="$BASE_DIR/logs"
RUN_LOG="$LOG_DIR/whatsapp-group-healthcheck.log"
ALERT_LOG="$LOG_DIR/whatsapp-group-healthcheck-alerts.log"
ALERT_CHANNEL="${ALERT_CHANNEL:-whatsapp}"
ALERT_TARGET="${ALERT_TARGET:-+593998956021}"
ALERT_COOLDOWN_SECONDS="${ALERT_COOLDOWN_SECONDS:-7200}"
ALERT_STATE_FILE="$LOG_DIR/whatsapp-group-healthcheck-last-alert.ts"

mkdir -p "$LOG_DIR"

TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

echo "[$TS] RUN start" >> "$RUN_LOG"
if "$CHECK_SCRIPT" >> "$RUN_LOG" 2>&1; then
  echo "[$TS] RUN ok" >> "$RUN_LOG"
else
  CODE=$?
  MSG="[$TS] ALERT healthcheck failed (exit=$CODE). Revisa: $RUN_LOG"
  echo "$MSG" | tee -a "$ALERT_LOG" >> "$RUN_LOG"
  logger -t openclaw-whatsapp-healthcheck "$MSG" || true

  NOW_EPOCH=$(date +%s)
  LAST_ALERT_EPOCH=0
  if [[ -f "$ALERT_STATE_FILE" ]]; then
    LAST_ALERT_EPOCH=$(cat "$ALERT_STATE_FILE" 2>/dev/null || echo 0)
  fi

  if (( NOW_EPOCH - LAST_ALERT_EPOCH >= ALERT_COOLDOWN_SECONDS )); then
    openclaw message send \
      --channel "$ALERT_CHANNEL" \
      --target "$ALERT_TARGET" \
      --message "🚨 OpenClaw healthcheck WhatsApp grupos FALLÓ. Revisa: $RUN_LOG (UTC $TS)" \
      >/dev/null 2>&1 || true
    echo "$NOW_EPOCH" > "$ALERT_STATE_FILE"
    echo "[$TS] ALERT sent (cooldown ${ALERT_COOLDOWN_SECONDS}s)" >> "$RUN_LOG"
  else
    REMAINING=$((ALERT_COOLDOWN_SECONDS - (NOW_EPOCH - LAST_ALERT_EPOCH)))
    echo "[$TS] ALERT suppressed by cooldown (${REMAINING}s remaining)" >> "$RUN_LOG"
  fi

  exit $CODE
fi
