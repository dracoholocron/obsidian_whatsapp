#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COOKIES_FILE="$ROOT_DIR/config/instagram-cookies.txt"
STATE_FILE="$ROOT_DIR/config/instagram-storage-state.json"
REFRESH_JS="$SCRIPT_DIR/refresh_instagram_cookies_playwright.js"
INGEST_PY="$SCRIPT_DIR/ingest_instagram_carousel_to_obsidian.py"

URL="${1:-}"
TITLE="${2:-}"

if [[ -z "$URL" ]]; then
  echo "Uso: $0 <instagram_post_url> [title]" >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/config"

refresh_cookies() {
  node "$REFRESH_JS" --out "$COOKIES_FILE" --state "$STATE_FILE"
}

if [[ ! -s "$COOKIES_FILE" ]]; then
  echo "[info] cookies no existen; intentando refrescar desde storage state..."
  if ! refresh_cookies; then
    echo "[warn] no se pudo refrescar sin login interactivo"
  fi
fi

if [[ -n "$TITLE" ]]; then
  set +e
  python3 "$INGEST_PY" "$URL" --title "$TITLE" --cookies-file "$COOKIES_FILE"
  rc=$?
  set -e
else
  set +e
  python3 "$INGEST_PY" "$URL" --cookies-file "$COOKIES_FILE"
  rc=$?
  set -e
fi

if [[ $rc -ne 0 ]]; then
  echo "[warn] primer intento falló; refrescando cookies y reintentando..."
  refresh_cookies
  if [[ -n "$TITLE" ]]; then
    python3 "$INGEST_PY" "$URL" --title "$TITLE" --cookies-file "$COOKIES_FILE"
  else
    python3 "$INGEST_PY" "$URL" --cookies-file "$COOKIES_FILE"
  fi
fi
