#!/usr/bin/env bash
# Kézi git-pull a trendfigyelo szerveren, a cron esti ablakától (*/30 19-23) függetlenül.
#
# A szerver tiszta TÜKÖR: csak fast-forward. Sosem készít merge-commitot; ha a HEAD
# valaha eltérne az origintől, hangosan elhasal, nem kavar bele a working-tree-be.
# A cron ugyanezt teszi --quiet-tal; ez a kézi változat kiírja, mi történt.
#
# Használat a szerveren:  bash scripts/kezi_pull.sh
set -euo pipefail

# Önmagát lövi be: a repo-gyökér a script mappájának szülője.
# Így nincs bedrótozott /home/trendfigyelo/... útvonal — bárhonnan működik.
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

elotte="$(git -C "$repo" rev-parse --short HEAD)"
echo "Repo:   $repo"
echo "Előtte: $elotte"

git -C "$repo" pull --ff-only

utana="$(git -C "$repo" rev-parse --short HEAD)"
if [ "$elotte" = "$utana" ]; then
  echo "Nincs változás (HEAD marad: $utana)."
else
  echo "Frissítve: $elotte → $utana"
  git -C "$repo" --no-pager log --oneline "$elotte..$utana"
fi
