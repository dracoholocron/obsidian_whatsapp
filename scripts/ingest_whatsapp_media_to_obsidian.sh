#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIO_INGEST="$SCRIPT_DIR/ingest_audio_note_to_obsidian.py"
WRITE_REMOTE="$SCRIPT_DIR/write_obsidian_note_remote.sh"

MEDIA_PATH="${1:-}"
TITLE="${2:-Nota de voz WhatsApp}"
MODEL="${3:-small}"

if [[ -z "$MEDIA_PATH" ]]; then
  echo "Uso: $0 <media_path> [title] [model]" >&2
  exit 1
fi

if [[ ! -f "$MEDIA_PATH" ]]; then
  echo "ERROR: archivo no existe: $MEDIA_PATH" >&2
  exit 1
fi

ext="${MEDIA_PATH##*.}"
ext="${ext,,}"

case "$ext" in
  ogg|opus|mp3|m4a|wav|aac|webm)
    python3 "$AUDIO_INGEST" "$MEDIA_PATH" --title "$TITLE" --model "$MODEL"
    ;;
  *)
    now_utc="$(date -u +"%Y-%m-%d %H:%M UTC")"
    content="# Archivo multimedia recibido

## Fuente
- Tipo: Archivo adjunto WhatsApp
- Ruta local: $MEDIA_PATH
- Extraído: $now_utc
- Tags: #adjunto #whatsapp #pendiente

## Nota
No se detectó formato de audio soportado para transcripción automática.
"
    "$WRITE_REMOTE" "00-Inbox/$(date -u +"%Y-%m")" "$TITLE" "$content"
    ;;
esac
