#!/usr/bin/env bash
# Elindít egy GitHub Actions workflow-t a szerverről (workflow_dispatch), hogy a napi
# gyűjtés IDŐBEN fusson — a GitHub best-effort ütemezésének késése helyett garantált
# indítás. A GitHub-cronok backupként megmaradnak; az idempotencia-őr dedup-olja őket.
#
# Használat:  bash scripts/trigger_workflow.sh napi.yml
#             bash scripts/trigger_workflow.sh youtube.yml
#
# A tokent egy chmod 600 fájlból olvassa (a repóba SOHA nem kerül):
#   alap:  $HOME/.config/trendfigyelo/gh_token
#   felül: GH_TOKEN_FILE környezeti változóval
# A token egy repo-scoped fine-grained PAT, KIZÁRÓLAG "Actions: Read and write" joggal.
#
# Cron-példa (szerver helyi ideje = Europe/Budapest; NINCS CRON_TZ):
#   0 9  * * *  bash /home/trendfigyelo/trendfigyelo/scripts/trigger_workflow.sh reggeli.yml >> ~/trigger.log 2>&1
#   0 21 * * *  bash /home/trendfigyelo/trendfigyelo/scripts/trigger_workflow.sh napi.yml    >> ~/trigger.log 2>&1
#   0 15 * * *  bash /home/trendfigyelo/trendfigyelo/scripts/trigger_workflow.sh youtube.yml >> ~/trigger.log 2>&1
set -euo pipefail

wf="${1:-}"
if [ -z "$wf" ]; then
  echo "HIBA: add meg a workflow-fájlt (pl. napi.yml)." >&2
  exit 2
fi

# Önmagát lövi be: a repo-gyökér a script mappájának szülője (nincs bedrótozott útvonal).
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

token_fajl="${GH_TOKEN_FILE:-$HOME/.config/trendfigyelo/gh_token}"
if [ ! -r "$token_fajl" ]; then
  echo "HIBA: a token-fájl nem olvasható: $token_fajl" >&2
  exit 3
fi
token="$(tr -d ' \t\r\n' < "$token_fajl")"
if [ -z "$token" ]; then
  echo "HIBA: a token-fájl üres: $token_fajl" >&2
  exit 3
fi

# owner/repo a git-remote-ból (https vagy ssh alak is jó): .../OWNER/REPO(.git)
remote="$(git -C "$repo" remote get-url origin)"
slug="$(printf '%s\n' "$remote" | sed -E 's#(git@[^:]+:|https?://[^/]+/)##; s#\.git$##')"
if ! printf '%s' "$slug" | grep -q '/'; then
  echo "HIBA: nem sikerült owner/repo-t kinyerni a remote-ból: $remote" >&2
  exit 4
fi

url="https://api.github.com/repos/${slug}/actions/workflows/${wf}/dispatches"
most="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# A dispatch sikerére a GitHub 204 No Content-et ad. A törzset elkülönítjük a státuszkódtól.
kod="$(curl -sS -o /tmp/trigger_workflow_valasz.$$ -w '%{http_code}' \
  --connect-timeout 15 --max-time 30 \
  -X POST "$url" \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${token}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -d '{"ref":"main"}')" || {
    echo "[$most] HIBA: a curl hívás elhasalt ($wf, $slug)." >&2
    rm -f "/tmp/trigger_workflow_valasz.$$"
    exit 5
  }

valasz="$(cat "/tmp/trigger_workflow_valasz.$$" 2>/dev/null || true)"
rm -f "/tmp/trigger_workflow_valasz.$$"

if [ "$kod" = "204" ]; then
  echo "[$most] OK: elindítva a(z) $wf a(z) $slug repóban (HTTP 204)."
else
  echo "[$most] HIBA: a(z) $wf indítása nem sikerült (HTTP $kod). Válasz: $valasz" >&2
  exit 1
fi
