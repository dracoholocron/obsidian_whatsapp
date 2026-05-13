#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${1:-$HOME/.openclaw/openclaw.json}"
LOG_PATH="${2:-$(ls -1t /tmp/openclaw/openclaw-*.log 2>/dev/null | head -n 1 || true)}"
TAIL_LINES="${TAIL_LINES:-8000}"

OBS_GID="120363425089204858@g.us"
CRM_GID="120363426530677595@g.us"
OBS_AGENT="obsidian-inbox-agent"
CRM_AGENT="pets-customer-agent"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "ERROR: config no encontrado: $CONFIG_PATH"
  exit 2
fi

if [[ -z "${LOG_PATH}" || ! -f "${LOG_PATH}" ]]; then
  echo "WARN: log no encontrado; validando solo config."
  LOG_PATH=""
fi

node - "$CONFIG_PATH" "$LOG_PATH" "$TAIL_LINES" "$OBS_GID" "$CRM_GID" "$OBS_AGENT" "$CRM_AGENT" <<'NODE'
const fs = require('fs');
const [,, configPath, logPath, tailLinesRaw, obsGid, crmGid, obsAgent, crmAgent] = process.argv;
const tailLines = Number(tailLinesRaw || 8000);

const cfg = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const bindings = Array.isArray(cfg.bindings) ? cfg.bindings : [];
const groups = cfg?.channels?.whatsapp?.groups || {};
const groupPolicy = cfg?.channels?.whatsapp?.groupPolicy;

function hasBinding(agentId, gid) {
  return bindings.some(b => {
    if (b?.agentId !== agentId) return false;
    // formato legacy: {peer: "group:<id>"}
    if (typeof b?.peer === 'string' && b.peer === `group:${gid}`) return true;
    // formato actual: {match:{channel:"whatsapp",peer:{kind:"group",id:"...@g.us"}}}
    return b?.match?.channel === 'whatsapp' &&
      b?.match?.peer?.kind === 'group' &&
      b?.match?.peer?.id === gid;
  });
}

const checks = [];
function addCheck(name, ok, detail) { checks.push({name, ok, detail}); }

addCheck('groupPolicy configurado', !!groupPolicy, `groupPolicy=${groupPolicy ?? 'undefined'}`);
addCheck('allowlist contiene Obsidian', !!groups[obsGid], groups[obsGid] ? JSON.stringify(groups[obsGid]) : 'missing');
addCheck('allowlist contiene CRM', !!groups[crmGid], groups[crmGid] ? JSON.stringify(groups[crmGid]) : 'missing');
addCheck('binding Obsidian correcto', hasBinding(obsAgent, obsGid), `${obsAgent} -> group:${obsGid}`);
addCheck('binding CRM correcto', hasBinding(crmAgent, crmGid), `${crmAgent} -> group:${crmGid}`);

let logChecks = [];
if (logPath && fs.existsSync(logPath)) {
  const lines = fs.readFileSync(logPath, 'utf8').split('\n').slice(-tailLines);

  function countContains(str) { return lines.filter(l => l.includes(str)).length; }
  function countRegex(rx) { return lines.filter(l => rx.test(l)).length; }

  const obsInbound = countContains(`Inbound message ${obsGid}`) + countContains(`\"from\":\"${obsGid}\"`);
  const crmInbound = countContains(`Inbound message ${crmGid}`) + countContains(`\"from\":\"${crmGid}\"`);

  const obsSession = countContains(`sessionKey=agent:${obsAgent}:whatsapp:group:${obsGid}`);
  const crmSession = countContains(`sessionKey=agent:${crmAgent}:whatsapp:group:${crmGid}`);

  const directAnomaly = countRegex(/Inbound message \+593998956021 -> \+593983675836 \(direct/) +
                        countRegex(/Inbound message \+593998956021 -> \+593995367612 \(direct/);

  logChecks = [
    { name: 'inbound grupo Obsidian visto en log reciente', ok: obsInbound > 0, detail: `hits=${obsInbound}` },
    { name: 'inbound grupo CRM visto en log reciente', ok: crmInbound > 0, detail: `hits=${crmInbound}` },
    { name: 'sessionKey Obsidian group ejecutado', ok: obsSession > 0, detail: `hits=${obsSession}` },
    { name: 'sessionKey CRM group ejecutado', ok: crmSession > 0, detail: `hits=${crmSession}` },
    { name: 'señales direct observadas (informativo)', ok: true, detail: `direct_hits=${directAnomaly}` },
  ];
}

const all = [...checks, ...logChecks];
const hardFailures = all.filter(c => !c.ok && !c.name.includes('informativo'));

console.log('=== WhatsApp Group Integrations Healthcheck ===');
console.log(`config: ${configPath}`);
if (logPath) console.log(`log: ${logPath} (tail ${tailLines} lines)`);

for (const c of all) {
  console.log(`${c.ok ? 'OK  ' : 'FAIL'} | ${c.name} | ${c.detail}`);
}

if (hardFailures.length) {
  console.log(`\nRESULTADO: FAIL (${hardFailures.length} check(s))`);
  process.exit(1);
}

console.log('\nRESULTADO: OK');
NODE
