#!/usr/bin/env bash
# Smoke examples for Stepsales Sales API MVP.
# Requires: DOGRAH_API_KEY, optional BASE_URL (default http://localhost:8000)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
API="${BASE_URL%/}/api/v1/stepsales"
KEY="${DOGRAH_API_KEY:?Set DOGRAH_API_KEY}"

auth=(-H "X-API-Key: ${KEY}" -H "Content-Type: application/json")

echo "== health =="
curl -fsS "${API}/health" | tee /tmp/stepsales-health.json
echo

echo "== packages =="
curl -fsS "${auth[@]}" "${API}/packages" | tee /tmp/stepsales-packages.json
echo

echo "== qualify =="
QUALIFY=$(curl -fsS "${auth[@]}" -X POST "${API}/leads/qualify" -d '{
  "company_name":"TechCorp GmbH",
  "contact_name":"Max Müller",
  "role":"HR Manager",
  "email":"max@techcorp.de",
  "phone":"+49301234567",
  "active_hiring":true,
  "roles_hiring_for":["Software Engineer","Sales Manager"],
  "urgency":"high",
  "timeline":"2 weeks",
  "budget_signal":"open",
  "interest_level":"high",
  "next_step":"send_offer"
}')
echo "$QUALIFY" | tee /tmp/stepsales-qualify.json
LEAD_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["lead_id"])' <<<"$QUALIFY")
echo "LEAD_ID=$LEAD_ID"

echo "== call outcome =="
curl -fsS "${auth[@]}" -X POST "${API}/calls/outcome" -d "{
  \"lead_id\":\"${LEAD_ID}\",
  \"call_id\":\"CALL-SMOKE-1\",
  \"outcome\":\"qualified\",
  \"summary\":\"Active hiring for 3 roles, wants an offer.\",
  \"interest_level\":\"high\",
  \"next_step\":\"send_offer\"
}" | tee /tmp/stepsales-outcome.json
echo

echo "== create offer =="
OFFER=$(curl -fsS "${auth[@]}" -X POST "${API}/offers/create" -d "{
  \"lead_id\":\"${LEAD_ID}\",
  \"package_id\":\"MULTI_M\",
  \"discount_percent\":10,
  \"discount_reason\":\"close_this_week\"
}")
echo "$OFFER" | tee /tmp/stepsales-offer.json
OFFER_ID=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["offer_id"])' <<<"$OFFER")
echo "OFFER_ID=$OFFER_ID"

echo "== payment link =="
PAY=$(curl -fsS "${auth[@]}" -X POST "${API}/payments/link" -d "{
  \"lead_id\":\"${LEAD_ID}\",
  \"offer_id\":\"${OFFER_ID}\"
}")
echo "$PAY" | tee /tmp/stepsales-pay.json
PAY_REF=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["payment_reference"])' <<<"$PAY")

echo "== mark paid =="
curl -fsS "${auth[@]}" -X POST "${API}/payments/mark-received" -d "{
  \"lead_id\":\"${LEAD_ID}\",
  \"payment_reference\":\"${PAY_REF}\",
  \"payment_method\":\"credit_card\"
}" | tee /tmp/stepsales-paid.json
echo

echo "== post-sale request =="
curl -fsS "${auth[@]}" -X POST "${API}/post-sale/request-data" -d "{
  \"lead_id\":\"${LEAD_ID}\",
  \"email\":\"max@techcorp.de\",
  \"package_id\":\"MULTI_M\"
}" | tee /tmp/stepsales-postsale.json
echo

echo "== lead =="
curl -fsS "${auth[@]}" "${API}/leads/${LEAD_ID}" | tee /tmp/stepsales-lead.json
echo
echo "PASS: Stepsales smoke flow completed for ${LEAD_ID}"
