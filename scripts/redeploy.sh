#!/usr/bin/env bash
# scripts/redeploy.sh
#
# One-command rebuild + restart for the PNEC Flask backend.
#
# Why this exists: there's no auto-deploy. After pushing changes to
# main, the Docker container has to be rebuilt + restarted manually
# to pick up the new code. This script does both with sensible
# defaults.
#
# Usage (from the repo root):
#   ./scripts/redeploy.sh
#
# Optional env:
#   PNEC_FLASK_API   — base URL to verify after restart
#                       (default: https://beasts.opencodingsociety.com)
#   PNEC_ADMIN_KEY   — admin key to use for health verification
#                       (default: skip verification)
#   SKIP_PULL=1      — don't `git pull` first
#   SKIP_HEALTH=1    — don't verify the health endpoint after restart

set -euo pipefail

API="${PNEC_FLASK_API:-https://beasts.opencodingsociety.com}"
KEY="${PNEC_ADMIN_KEY:-}"

cd "$(dirname "$0")/.."

echo "── PNEC Flask redeploy ──────────────────────────────"
echo ""

if [ "${SKIP_PULL:-0}" != "1" ]; then
  echo "1. Pulling latest main…"
  git pull origin main || { echo "   git pull failed. Continuing with local code."; }
  echo ""
else
  echo "1. SKIP_PULL=1 — skipping git pull"; echo ""
fi

echo "2. Rebuilding container image (this may take a minute)…"
docker compose build --pull
echo ""

echo "3. Restarting container…"
docker compose up -d
echo ""

# Wait a moment for the container to start serving traffic
sleep 3

if [ "${SKIP_HEALTH:-0}" != "1" ]; then
  echo "4. Verifying /api/admin/publish/health…"
  if [ -z "$KEY" ]; then
    echo "   PNEC_ADMIN_KEY not set — skipping authenticated health check."
    echo "   Run: curl -H \"X-PNEC-Admin-Key: \$KEY\" $API/api/admin/publish/health"
  else
    set +e
    code=$(curl -sS -o /tmp/pnec-redeploy-health.json -w "%{http_code}" \
                -H "X-PNEC-Admin-Key: $KEY" \
                -H "Accept: application/json" \
                "$API/api/admin/publish/health")
    set -e
    if [ "$code" = "200" ]; then
      echo "   ✓ Health endpoint returned 200"
      python3 -c "
import json, sys
d = json.load(open('/tmp/pnec-redeploy-health.json'))
print('     github:', '✓' if d.get('github',{}).get('ok') else '✗', '·', (d.get('github') or {}).get('full_name') or (d.get('github') or {}).get('error',''))
print('     groq:  ', '✓' if d.get('groq',{}).get('ok') else '✗', '·', (d.get('groq') or {}).get('model') or (d.get('groq') or {}).get('error',''))
" 2>/dev/null || cat /tmp/pnec-redeploy-health.json
    else
      echo "   ✗ Health endpoint returned $code — backend may not be fully up. Check:"
      echo "     docker compose logs --tail=50 web"
      exit 1
    fi
  fi
fi

echo ""
echo "── Done. Container is running with the latest code. ─"
