#!/usr/bin/env bash
# Pull main and restart, if anything changed. Run by dori-update.timer on the instance.
#
# The rule here is that a bad push must not take the site down: nothing restarts until the
# new code at least imports, and if the service comes back unhealthy the whole working tree
# goes back to the commit that was serving a minute ago. An auto-updating demo site is only
# a good idea if it can undo itself.

set -uo pipefail

REPO=/opt/dori
PORT=8000
LOG=/var/log/dori-update.log
exec >>"$LOG" 2>&1

cd "$REPO" || exit 1
flock -n /tmp/dori-update.lock true || { echo "$(date -Is) another update is running"; exit 0; }
exec 9>/tmp/dori-update.lock
flock -n 9 || exit 0

git fetch --quiet origin main || { echo "$(date -Is) fetch failed"; exit 1; }
WAS=$(git rev-parse HEAD)
NOW=$(git rev-parse origin/main)
[ "$WAS" = "$NOW" ] && exit 0

echo "=== $(date -Is) ${WAS:0:8} -> ${NOW:0:8} ==="
CHANGED=$(git diff --name-only "$WAS" "$NOW")
WEB_CHANGED=$(grep -cE '^apps/web/' <<<"$CHANGED" || true)

# Unit files ship with the code, so a change to how the service runs reaches the instance the
# same way a change to the code does. Previously they only updated on a full redeploy, which
# is how the guardrail ids on this box went stale.
install_units() {
  local changed=0
  for unit in dori.service dori-update.service dori-update.timer; do
    if ! cmp -s "$REPO/scripts/$unit" "/etc/systemd/system/$unit"; then
      install -m 0644 "$REPO/scripts/$unit" "/etc/systemd/system/$unit"
      echo "installed $unit"
      changed=1
    fi
  done
  [ "$changed" = 1 ] && systemctl daemon-reload
  return 0
}

build() {
  git reset --hard --quiet "$1"
  install_units
  if grep -q 'services/api/requirements.txt' <<<"$CHANGED"; then
    "$REPO/.venv/bin/pip" install --quiet -r "$REPO/services/api/requirements.txt" || return 1
  fi
  if [ "$WEB_CHANGED" -gt 0 ]; then
    ( cd "$REPO/apps/web" && npm ci --silent --no-audit --no-fund && npm run build ) || return 1
  fi
  return 0
}

rollback() {
  echo "rolling back to ${WAS:0:8}"
  build "$WAS" || echo "rollback build failed too"
  systemctl restart dori
}

if ! build "$NOW"; then
  echo "build failed"
  rollback
  exit 1
fi

# Cheapest possible smoke test: does the app even import?
if ! ( cd "$REPO/services/api" && "$REPO/.venv/bin/python" -c "import app.serve" >/dev/null 2>&1 ); then
  echo "new code does not import"
  rollback
  exit 1
fi

systemctl restart dori
for _ in $(seq 1 10); do
  sleep 2
  if curl -fs -m 4 "http://localhost:$PORT/api/health" >/dev/null 2>&1; then
    echo "healthy at ${NOW:0:8}"
    exit 0
  fi
done

echo "unhealthy after restart"
rollback
exit 1
