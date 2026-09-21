#!/usr/bin/env bash
# Viddra API — curl quickstart: submit -> poll -> get the MP4 URL.
#
# Requires:  export VIDDRA_API_KEY="your-key-here"   (https://viddra.com/console/keys/)
# Usage:     bash curl_quickstart.sh
# Docs:      https://viddra.com/docs/
set -euo pipefail

API="https://api.viddra.com"
: "${VIDDRA_API_KEY:?Set the VIDDRA_API_KEY environment variable first (https://viddra.com/console/keys/)}"

MODEL="${MODEL:-wan2.6}"
PROMPT="${PROMPT:-A cinematic shot of a neon-lit city street in the rain, ultra-detailed, 4k}"

# 1. Submit the generation task — 202 Accepted, cost is held from the balance.
RESP=$(curl -s -X POST "$API/v1/video/generations" \
  -H "Authorization: Bearer $VIDDRA_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"prompt\": \"$PROMPT\",
    \"duration\": 5,
    \"resolution\": \"720p\",
    \"aspect_ratio\": \"16:9\"
  }")

# Error envelope looks like {"error":{"code":"...","message":"..."}}
if echo "$RESP" | grep -q '"error"'; then
  echo "Submit failed: $RESP" >&2
  exit 1
fi

TASK_ID=$(printf '%s' "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
HOLD=$(printf '%s' "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("hold_usd","?"))')
echo "Submitted: id=$TASK_ID hold_usd=$HOLD"

# 2. Poll every 5s until the status is succeeded / failed.
for _ in $(seq 1 180); do # up to ~15 min
  sleep 5
  STATUS_JSON=$(curl -s "$API/v1/video/generations/$TASK_ID" \
    -H "Authorization: Bearer $VIDDRA_API_KEY")
  STATUS=$(printf '%s' "$STATUS_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')
  echo "  status=$STATUS"
  case "$STATUS" in
    succeeded|failed) break ;;
  esac
done

# 3. Print the result. Failed tasks refund the held amount automatically.
printf '%s' "$STATUS_JSON" | python3 -c '
import json, sys
t = json.load(sys.stdin)
if t["status"] == "succeeded":
    print(f"cost_usd={t.get(\"cost_usd\")}")
    print(f"video_url={t.get(\"video_url\") or t.get(\"result_url\")}")
else:
    print(f"task {t[\"status\"]}: {t.get(\"error\")}", file=sys.stderr)
    sys.exit(1)
'
