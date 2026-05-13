#!/usr/bin/env bash
set -euo pipefail

HOST="${OBSIDIAN_SSH_HOST:-100.127.140.90}"
USER_NAME="${OBSIDIAN_SSH_USER:-USER}"
VAULT_WIN="${OBSIDIAN_VAULT_WIN:-C:\\obsidian\\vault}"
SUBDIR="${1:-00-Inbox}"
TITLE="${2:-Inbox Note}"
CONTENT="${3:-}"

TS="$(date +%Y-%m-%d_%H-%M-%S)"
SAFE_TITLE="$(echo "$TITLE" | tr -cd '[:alnum:]._ -' | sed 's/ /_/g')"
FILE_WIN="${VAULT_WIN}\\${SUBDIR}\\${TS}__${SAFE_TITLE}.md"

PS_FILE="${FILE_WIN//\'/''}"
DOC="# ${TITLE}\n\n${CONTENT}\n"
DOC_B64="$(printf "%s" "$DOC" | base64 -w0)"

ssh -o ConnectTimeout=10 "${USER_NAME}@${HOST}" "powershell -NoProfile -Command \"\
\$path='${PS_FILE}'; \
\$dir = Split-Path -Parent \$path; \
New-Item -ItemType Directory -Force -Path \$dir | Out-Null; \
\$bytes = [Convert]::FromBase64String('${DOC_B64}'); \
\$text = [Text.Encoding]::UTF8.GetString(\$bytes); \
[IO.File]::WriteAllText(\$path, \$text, [Text.UTF8Encoding]::new(\$false)); \
Write-Output \$path\""
