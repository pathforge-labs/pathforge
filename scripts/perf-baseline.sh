#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# PathForge — Performance Baseline & Regression Gate
# ─────────────────────────────────────────────────────────────
# T3 / Sprint 56 — closes N-6 in MASTER_PRODUCTION_READINESS.md.
# Captures p50/p95 for the 17 baseline-tracked endpoints (health +
# 12 intelligence dashboards + auth) and either:
#
#   * **CAPTURE mode** (default) — writes a JSON baseline + CSV
#     diff-friendly output to `docs/baselines/`.
#   * **COMPARE mode** (`--compare-to=<path>`) — re-runs the same
#     workload, compares each endpoint's p95 to the pinned baseline,
#     and exits 1 on any endpoint regressing by > THRESHOLD percent.
#
# Usage
# -----
#
#   # Capture against local API
#   AUTH_TOKEN=<jwt> ./scripts/perf-baseline.sh \
#       --out=docs/baselines/2026-Q2.json
#
#   # Compare current vs pinned (CI gate)
#   AUTH_TOKEN=<jwt> ./scripts/perf-baseline.sh \
#       --compare-to=docs/baselines/2026-Q2.json \
#       --threshold=25
#
# AUTH_TOKEN is required for the intelligence endpoints (all require
# login).  Obtain via:
#   curl -s -X POST $API_BASE_URL/api/v1/auth/login \
#     -H 'Content-Type: application/json' \
#     -d '{"email":"...","password":"..."}' | jq -r .access_token
#
# Prerequisites
# -------------
#   - curl, bc, sort, awk, jq (jq required for JSON output / compare)
#   - Node.js (for Lighthouse; web baselines only)
#   - API running at API_BASE_URL (default: http://localhost:8000)
#   - Web running at WEB_BASE_URL (default: http://localhost:3000)
#
# Output
# ------
#   docs/baselines/api-<TIMESTAMP>.csv         — p50/p95 per endpoint
#   docs/baselines/<OUT>.json                  — pinned baseline JSON
#   docs/baselines/lighthouse-<TS>/            — Lighthouse HTML+JSON
#
# ─────────────────────────────────────────────────────────────

set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
WEB_BASE_URL="${WEB_BASE_URL:-http://localhost:3000}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
RESULTS_DIR="./docs/baselines"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ITERATIONS=20
API_ONLY=false
WEB_ONLY=false
OUT_PATH=""
COMPARE_TO=""
THRESHOLD=25  # percent — drift detector, not a fitness gate

for arg in "$@"; do
  case $arg in
    --api-only) API_ONLY=true ;;
    --web-only) WEB_ONLY=true ;;
    --out=*) OUT_PATH="${arg#*=}" ;;
    --compare-to=*) COMPARE_TO="${arg#*=}"; API_ONLY=true ;;
    --threshold=*) THRESHOLD="${arg#*=}" ;;
    -h|--help)
      sed -n '2,46p' "$0"
      exit 0
      ;;
  esac
done

mkdir -p "$RESULTS_DIR"

CSV="$RESULTS_DIR/api-${TIMESTAMP}.csv"
DEFAULT_JSON="$RESULTS_DIR/api-${TIMESTAMP}.json"
JSON="${OUT_PATH:-$DEFAULT_JSON}"

# Mode banner ------------------------------------------------------
echo "═══════════════════════════════════════════════════"
if [ -n "$COMPARE_TO" ]; then
  echo "  PathForge — Performance Regression Gate"
  echo "  Mode      : COMPARE (threshold ${THRESHOLD}%)"
  echo "  Baseline  : $COMPARE_TO"
else
  echo "  PathForge — Performance Baseline Capture"
  echo "  Mode      : CAPTURE → $JSON"
fi
echo "  Timestamp : $TIMESTAMP"
echo "  Iterations: $ITERATIONS per endpoint"
echo "  API       : $API_BASE_URL"
echo "═══════════════════════════════════════════════════"

# ── Dependency check ─────────────────────────────────────────
# Verify all required tools up-front. Without ``bc`` the ms conversion
# silently returned 0, which then falsely passed the regression gate
# at every endpoint (Gemini medium — silent-failure class). ``jq`` is
# always required because capture mode now generates JSON by default.
_missing=()
for _bin in curl bc jq sort awk; do
  if ! command -v "$_bin" &> /dev/null; then
    _missing+=("$_bin")
  fi
done
if [ ${#_missing[@]} -gt 0 ]; then
  echo "✗ Missing required tools: ${_missing[*]}" >&2
  echo "  Install all of: curl bc jq coreutils (sort) gawk" >&2
  exit 2
fi
unset _bin _missing

# ── Compare mode requires the baseline file ──────────────────
if [ -n "$COMPARE_TO" ]; then
  if [ ! -f "$COMPARE_TO" ]; then
    echo "✗ Baseline file not found: $COMPARE_TO" >&2
    exit 2
  fi
fi

# ── Output buffers ───────────────────────────────────────────
JSON_ENTRIES=()
REGRESSIONS=0
TOTAL_COMPARED=0

# ── p50 / p95 measurement ────────────────────────────────────
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
    t_ms=$(printf '%.0f' "$(echo "$t * 1000" | bc 2>/dev/null || echo 0)")
    times+=("$t_ms")
  done

  sorted=($(printf '%s\n' "${times[@]}" | sort -n))
  p50_idx=$(( ITERATIONS * 50 / 100 - 1 ))
  p95_idx=$(( ITERATIONS * 95 / 100 - 1 ))
  p50=${sorted[$p50_idx]:-0}
  p95=${sorted[$p95_idx]:-0}

  if [ -n "$COMPARE_TO" ]; then
    base_p95=$(jq -r --arg ep "$endpoint" \
      '.endpoints[] | select(.endpoint == $ep) | .p95_ms' \
      "$COMPARE_TO" 2>/dev/null || echo "null")
    if [ "$base_p95" = "null" ] || [ -z "$base_p95" ]; then
      printf 'p95=%4dms (baseline absent)\n' "$p95"
    else
      TOTAL_COMPARED=$((TOTAL_COMPARED + 1))
      if [ "$base_p95" -le 0 ]; then
        printf 'p95=%4dms (baseline=0, skipping ratio check)\n' "$p95"
      else
        delta_pct=$(( (p95 - base_p95) * 100 / base_p95 ))
        flag=""
        if [ "$delta_pct" -gt "$THRESHOLD" ]; then
          flag=" 🚨 REGRESSION"
          REGRESSIONS=$((REGRESSIONS + 1))
        fi
        printf 'p95=%4dms  (baseline=%4dms, Δ=%+d%%)%s\n' \
          "$p95" "$base_p95" "$delta_pct" "$flag"
      fi
    fi
  else
    echo "p50=${p50}ms  p95=${p95}ms"
  fi

  printf '%s,%s,%s,%s,%s\n' \
    "$label" "$endpoint" "${p50}ms" "${p95}ms" "$TIMESTAMP" >> "$CSV"

  if [ -z "$COMPARE_TO" ]; then
    # Build the per-endpoint JSON object via jq so labels / endpoints
    # containing quotes or backslashes don't corrupt the baseline file
    # (Gemini medium — printf doesn't escape JSON strings).
    JSON_ENTRIES+=("$(jq -nc \
      --arg label "$label" \
      --arg endpoint "$endpoint" \
      --argjson p50_ms "$p50" \
      --argjson p95_ms "$p95" \
      --argjson iterations "$ITERATIONS" \
      '{label: $label, endpoint: $endpoint, p50_ms: $p50_ms, p95_ms: $p95_ms, iterations: $iterations}')")
  fi
}

# ── API baselines ─────────────────────────────────────────────
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

  # Write JSON baseline (capture mode only). Pipe the per-endpoint
  # entries into ``jq -s`` so the final structure is always valid JSON
  # — manual loop-and-printf assembly is prone to trailing commas and
  # mis-quoted strings (Gemini medium — JSON correctness).
  if [ -z "$COMPARE_TO" ] && [ ${#JSON_ENTRIES[@]} -gt 0 ]; then
    printf '%s\n' "${JSON_ENTRIES[@]}" | jq -s \
      --arg captured_at "$TIMESTAMP" \
      --argjson iterations "$ITERATIONS" \
      --arg api_base_url "$API_BASE_URL" \
      '{captured_at: $captured_at, iterations: $iterations, api_base_url: $api_base_url, endpoints: .}' \
      > "$JSON"
    echo "✓ JSON baseline saved → $JSON"
  fi
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

# ── Compare mode summary ─────────────────────────────────────
if [ -n "$COMPARE_TO" ]; then
  echo ""
  echo "═══════════════════════════════════════════════════"
  echo "  Regression summary"
  echo "    Endpoints compared: $TOTAL_COMPARED"
  echo "    Threshold         : ${THRESHOLD}% over baseline p95"
  echo "    Regressions       : $REGRESSIONS"
  echo "═══════════════════════════════════════════════════"
  if [ "$REGRESSIONS" -gt 0 ]; then
    echo ""
    echo "✗ Performance regression detected on $REGRESSIONS endpoint(s)."
    echo "  Investigate or refresh the baseline (see docs/baselines/README.md)."
    exit 1
  fi
  echo ""
  echo "✓ All endpoints within ${THRESHOLD}% of baseline p95."
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Baseline capture complete."
echo "  Results: $RESULTS_DIR/"
echo "═══════════════════════════════════════════════════"
