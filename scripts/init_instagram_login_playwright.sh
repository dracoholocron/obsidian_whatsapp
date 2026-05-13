#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
mkdir -p "$ROOT_DIR/config"
node "$SCRIPT_DIR/refresh_instagram_cookies_playwright.js" \
  --interactive-login \
  --timeout-sec 300 \
  --out "$ROOT_DIR/config/instagram-cookies.txt" \
  --state "$ROOT_DIR/config/instagram-storage-state.json"
