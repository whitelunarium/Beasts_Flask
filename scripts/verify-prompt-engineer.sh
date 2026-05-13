#!/bin/bash
# verify-prompt-engineer.sh
#
# Smoke-test the /api/admin/ai/prompt-engineer endpoint live in
# production against all three target AIs. Reports placeholder
# substitution health, prompt-token usage (must stay < 12K Groq TPM),
# and the first 200 chars of each engineered prompt for spot-checking
# the format-hint adherence.
#
# Usage:
#   ./scripts/verify-prompt-engineer.sh
#
# Required env:
#   PNEC_ADMIN_KEY  — defaults to the production key
#
set -e

ADMIN_KEY="${PNEC_ADMIN_KEY:-VUL5xq9Pue3s64cNHSACYdeXKvb3}"
API="https://beasts.opencodingsociety.com/api/admin/ai/prompt-engineer"
TARGETS=("claude" "gemini" "chatgpt")

# Use a small page to minimise rate-limit risk during the smoke test
PAGE="pages/contact.html"
DESC="Replace the contact form intro paragraph with a one-line friendly welcome."

echo "=== /api/admin/ai/prompt-engineer smoke-test ==="
echo "page=$PAGE  description=$DESC"
echo

for ai in "${TARGETS[@]}"; do
  echo "--- target_ai: $ai ---"
  out=$(curl -s -X POST \
    -H "X-PNEC-Admin-Key: $ADMIN_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"path\":\"$PAGE\",\"description\":\"$DESC\",\"target_ai\":\"$ai\"}" \
    "$API")
  python3 - <<PY
import json
d = json.loads('''$out''')
ok = d.get('ok')
err = d.get('error')
ph = d.get('placeholder_handled')
toks = (d.get('usage') or {}).get('prompt_tokens')
prompt = d.get('prompt') or ''
print(f"  ok={ok}  err={err}  placeholder={ph}  prompt_tokens={toks}  prompt_len={len(prompt)}")
print(f"  head: {prompt[:200]!r}")
PY
  echo
  # Small sleep so we don't blow through the per-minute rate-limit
  sleep 8
done

echo "=== done ==="
