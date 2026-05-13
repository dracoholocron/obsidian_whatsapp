#!/usr/bin/env bash
set -euo pipefail

URL="${1:-}"
if [[ -z "$URL" ]]; then
  echo "Uso: $0 <tiktok-url>" >&2
  exit 2
fi

JSON="$(yt-dlp --dump-single-json --no-warnings --skip-download "$URL" 2>/dev/null || true)"
if [[ -z "$JSON" ]]; then
  echo "NO_METADATA"
  exit 1
fi

TITLE="$(jq -r '.title // "(sin titulo)"' <<<"$JSON")"
UPLOADER="$(jq -r '.uploader // .channel // "(desconocido)"' <<<"$JSON")"
DURATION="$(jq -r '.duration // empty' <<<"$JSON")"
DESC="$(jq -r '.description // ""' <<<"$JSON")"
WEBURL="$(jq -r '.webpage_url // .original_url // empty' <<<"$JSON")"
TS="$(date -u +"%Y-%m-%d %H:%M UTC")"

if [[ -n "$DURATION" && "$DURATION" != "null" ]]; then
  DUR_LINE="- Duración: ${DURATION}s"
else
  DUR_LINE="- Duración: no disponible"
fi

cat <<EOF
## Fuente TikTok
- URL enviada: $URL
- URL resuelta: ${WEBURL:-$URL}
- Autor: $UPLOADER
$DUR_LINE
- Extraído: $TS

## Título
$TITLE

## Descripción
${DESC:-Sin descripción disponible}
EOF
