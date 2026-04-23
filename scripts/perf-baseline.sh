#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# PathForge — Performance Baseline Script
# ─────────────────────────────────────────────────────────────
# Sprint 30 WS-5 / N-6: Captures p50+p95 for all 12 intelligence
# dashboard endpoints + Lighthouse web baselines.
#
# Usage:
#   AUTH_TOKEN=<jwt> ./scripts/perf-baseline.sh [--api-only] [--web-only]
#
# AUTH_TOKEN is required for the intelligence endpoints (all require login).
# Obtain via:
#   curl -s -X POST $API_BASE_URL/api/v1/auth/login \
#     -H 'Content-Type: application/json' \
#     -d '{"email":"...","password":"..."}' | jq -r .access_token
#
# Prerequisites:
#   - curl, bc, sort, awk (all standard)
#   - Node.js (for Lighthouse; web baselines only)
#   - API running at API_BASE_URL (default: http://localhost:8000)
#   - Web running at WEB_BASE_URL (default: http://localhost:3000)
#
# Output:
#   docs/baselines/api-<TIMESTAMP>.csv   — p50/p95 per endpoint
#   docs/baselines/lighthouse-<TS>/      — Lighthouse HTML+JSON

set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
WEB_BASE_URL="${WEB_BASE_URL:-http://localhost:3000}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
RESULTS_DIR="./docs/baselines"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ITERATIONS=20
API_ONLY=false
WEB_ONLY=false

for arg in "$@"; do
  case $arg in
    --api-only) API_ONLY=true ;;
    --web-only) WEB_ONLY=true ;;
  esac
done

mkdir -p "$RESULTS_DIR"

CSV="$RESULTS_DIR/api-${TIMESTAMP}.csv"

echo "═══════════════════════════════════════════════════"
echo "  PathForge — Performance Baseline Capture"
echo "  Timestamp : $TIMESTAMP"
echo "  Iterations: $ITERATIONS per endpoint"
echo "  API       : $API_BASE_URL"
echo "═══════════════════════════════════════════════════"

# ── p50 / p95 measurement ───────────────────────────────────

measure() {
  local label=$1
  local endpoint=$2
  local auth=${3:-false}
  local times=()

  printf "▸ %-55s " "$label"

  local auth_flag=()
  if [ "$auth" = "true" ] && [ -n "$AUTH_TOKEN" ]; then
    auth_flag=(-H "Authorization: Bearer $AUTH_TOKEN")
  fi

  for _ in $(seq 1 "$ITERATIONS"); do
    t=$(curl -s -o /dev/null -w "%{time_total}" \
      "${auth_flag[@]+"${auth_flag[@]}"}" \
      --max-time 30 \
      "$API_BASE_URL$endpoint" 2>/dev/null || echo "0")
    # Convert to ms (integer)
    t_ms=$(printf '%.0f' "$(echo "$t * 1000" | bc 2>/dev/null || echo 0)")
    times+=("$t_ms")
  done

  sorted=($(printf '%s\n' "${times[@]}" | sort -n))
  p50_idx=$(( ITERATIONS * 50 / 100 - 1 ))
  p95_idx=$(( ITERATIONS * 95 / 100 - 1 ))
  p50=${sorted[$p50_idx]:-0}
  p95=${sorted[$p95_idx]:-0}

  echo "p50=${p50}ms  p95=${p95}ms"
  printf '%s,%s,%s,%s,%s\n' \
    "$label" "$endpoint" "${p50}ms" "${p95}ms" "$TIMESTAMP" >> "$CSV"
}

# ── API baselines ────────────────────────────────────────────

if [ "$WEB_ONLY" = false ]; then
  echo ""
  echo "── Infrastructure ───────────────────────────────"
  printf 'label,endpoint,p50,p95,timestamp\n' > "$CSV"

  measure "Health (liveness)"    "/api/v1/health"       false
  measure "Health (readiness)"   "/api/v1/health/ready" false

  if [ -z "$AUTH_TOKEN" ]; then
    echo ""
    echo "⚠  AUTH_TOKEN not set — skipping authenticated intelligence endpoints."
    echo "   Set AUTH_TOKEN=<jwt> to capture p50/p95 for all 12 engines."
  else
    echo ""
    echo "── Intelligence Engine Dashboards ───────────────"

    measure "Career DNA"              "/api/v1/career-dna"                        true
    measure "Career DNA summary"      "/api/v1/career-dna/summary"                true
    measure "Skill genome"            "/api/v1/career-dna/skills"                 true
    measure "Threat Radar overview"   "/api/v1/threat-radar"                      true
    measure "Threat Radar signals"    "/api/v1/threat-radar/signals"              true
    measure "Salary dashboard"        "/api/v1/salary-intelligence"               true
    measure "Salary estimate"         "/api/v1/salary-intelligence/estimate"      true
    measure "Salary impacts"          "/api/v1/salary-intelligence/impacts"       true
    measure "Salary trajectory"       "/api/v1/salary-intelligence/trajectory"    true
    measure "Skill Decay dashboard"   "/api/v1/skill-decay"                       true
    measure "Skill freshness"         "/api/v1/skill-decay/freshness"             true
    measure "Skill market demand"     "/api/v1/skill-decay/market-demand"         true
    measure "Skill velocity"          "/api/v1/skill-decay/velocity"              true
    measure "Reskilling pathways"     "/api/v1/skill-decay/reskilling"            true
    measure "Recommendations dash"    "/api/v1/recommendations/dashboard"         true
    measure "Recommendations list"    "/api/v1/recommendations"                   true
    measure "Recommendation batches"  "/api/v1/recommendations/batches"           true
  fi

  echo ""
  echo "✓ API baselines saved → $CSV"
fi

# ── Lighthouse web baselines ─────────────────────────────────

if [ "$API_ONLY" = false ]; then
  echo ""
  echo "── Lighthouse Web Baselines ─────────────────────"

  if command -v npx &> /dev/null; then
    LH_OUT="$RESULTS_DIR/lighthouse-${TIMESTAMP}"
    mkdir -p "$LH_OUT"

    lh_page() {
      local name=$1
      local path=$2
      echo "▸ Lighthouse: $path"
      npx -y lighthouse "$WEB_BASE_URL$path" \
        --output=json,html \
        --output-path="$LH_OUT/$name" \
        --chrome-flags="--headless --no-sandbox --disable-gpu" \
        --quiet \
        2>/dev/null || echo "  ⚠ Lighthouse failed (is the web server running?)"
    }

    lh_page "login"      "/login"
    lh_page "dashboard"  "/dashboard"
    lh_page "career-dna" "/dashboard/career-dna"

    echo "✓ Lighthouse reports saved → $LH_OUT/"
  else
    echo "  ⚠ npx not found — skipping Lighthouse"
  fi
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Baseline capture complete."
echo "  Results: $RESULTS_DIR/"
echo "═══════════════════════════════════════════════════"
