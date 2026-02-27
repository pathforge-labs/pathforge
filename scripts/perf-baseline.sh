#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# PathForge — Performance Baseline Script
# ─────────────────────────────────────────────────────────────
# Sprint 30 WS-5: Captures Lighthouse and API P95 baselines.
#
# Usage:
#   ./scripts/perf-baseline.sh [--api-only] [--web-only]
#
# Prerequisites:
#   - Node.js (for Lighthouse)
#   - curl (for API timing)
#   - API running at API_BASE_URL (default: http://localhost:8000)
#   - Web running at WEB_BASE_URL (default: http://localhost:3000)

set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
WEB_BASE_URL="${WEB_BASE_URL:-http://localhost:3000}"
RESULTS_DIR="./perf-baselines"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
API_ONLY=false
WEB_ONLY=false

# Parse flags
for arg in "$@"; do
  case $arg in
    --api-only) API_ONLY=true ;;
    --web-only) WEB_ONLY=true ;;
  esac
done

mkdir -p "$RESULTS_DIR"

echo "═══════════════════════════════════════════════════"
echo "  PathForge — Performance Baseline Capture"
echo "  Timestamp: $TIMESTAMP"
echo "═══════════════════════════════════════════════════"

# ── API P95 Response Time Measurement ──────────────────────

measure_api_p95() {
  local endpoint=$1
  local label=$2
  local times=()
  local iterations=20

  echo ""
  echo "▸ API: $label ($endpoint)"

  for i in $(seq 1 $iterations); do
    time_ms=$(curl -s -o /dev/null -w "%{time_total}" \
      "$API_BASE_URL$endpoint" --max-time 10 2>/dev/null || echo "0")
    time_ms_int=$(echo "$time_ms * 1000" | bc 2>/dev/null || echo "0")
    times+=("$time_ms_int")
  done

  # Sort and get P95 (95th percentile)
  sorted=($(printf '%s\n' "${times[@]}" | sort -n))
  p95_index=$(( (iterations * 95 / 100) - 1 ))
  p95=${sorted[$p95_index]:-0}

  echo "  P95: ${p95}ms (over ${iterations} requests)"
  echo "$label,$endpoint,${p95}ms,$TIMESTAMP" >> "$RESULTS_DIR/api-baselines.csv"
}

if [ "$WEB_ONLY" = false ]; then
  echo ""
  echo "── API Response Time Baselines ──────────────────"

  # Initialize CSV header
  echo "label,endpoint,p95,timestamp" > "$RESULTS_DIR/api-baselines.csv"

  measure_api_p95 "/api/v1/health" "Health (liveness)"
  measure_api_p95 "/api/v1/health/ready" "Health (readiness)"

  echo ""
  echo "✓ API baselines saved to $RESULTS_DIR/api-baselines.csv"
fi

# ── Lighthouse Web Baselines ───────────────────────────────

if [ "$API_ONLY" = false ]; then
  echo ""
  echo "── Lighthouse Web Baselines ─────────────────────"

  if command -v npx &> /dev/null; then
    LIGHTHOUSE_OUT="$RESULTS_DIR/lighthouse-${TIMESTAMP}"
    mkdir -p "$LIGHTHOUSE_OUT"

    echo ""
    echo "▸ Running Lighthouse on: $WEB_BASE_URL/login"
    npx -y lighthouse "$WEB_BASE_URL/login" \
      --output=json,html \
      --output-path="$LIGHTHOUSE_OUT/login" \
      --chrome-flags="--headless --no-sandbox" \
      --quiet \
      2>/dev/null || echo "  ⚠ Lighthouse failed (is the web server running?)"

    echo "✓ Lighthouse reports saved to $LIGHTHOUSE_OUT/"
  else
    echo "  ⚠ npx not found — skipping Lighthouse"
  fi
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Baseline capture complete."
echo "  Results: $RESULTS_DIR/"
echo "═══════════════════════════════════════════════════"
