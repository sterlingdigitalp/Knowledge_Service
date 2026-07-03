#!/bin/zsh
# Canonical Knowledge_Service verification — one command, one PASS/FAIL summary.
#
# Usage:
#   bin/verify.sh              # standard verification (no slow certifiers)
#   VERIFY_FULL=1 bin/verify.sh   # include certify_phase51_runtime.py
#
# Exit 0 when all required steps pass (integration skips are OK).

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${KNOWLEDGE_SERVICE:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$ROOT" || exit 1

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  PYTHON="$ROOT/.venv/bin/python3"
else
  PYTHON="python3"
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

FAILURES=0
REPORT=()
SKIPS=""

_run() {
  local name="$1"
  shift
  echo ""
  echo "=== $name ==="
  if "$@"; then
    REPORT+=("PASS  $name")
    echo "→ PASS"
  else
    REPORT+=("FAIL  $name")
    FAILURES=$((FAILURES + 1))
    echo "→ FAIL"
  fi
}

_pytest() {
  local label="$1"
  shift
  local out
  out=$("$PYTHON" -m pytest "$@" -q --tb=no 2>&1) || return 1
  echo "$out" | tail -3
  if echo "$out" | rg -q " failed "; then
    return 1
  fi
  if echo "$out" | rg -q " skipped"; then
    SKIPS="${SKIPS}${SKIPS:+, }${label}"
  fi
  return 0
}

_run "compileall" "$PYTHON" -m compileall -q "$ROOT/src/knowledge_service"

_run "offline tests" _pytest offline \
  "$ROOT/tests" "$ROOT/failure_tests" "$ROOT/property_tests" "$ROOT/performance_tests"

_run "smoke tests" _pytest smoke "$ROOT/tests/smoke"

_run "production tests" _pytest production "$ROOT/tests/production"

_run "intelligence tests" _pytest intelligence "$ROOT/tests/intelligence"

_run "runtime3 tests" _pytest runtime3 "$ROOT/tests/runtime3"

_run "integration tests" _pytest integration "$ROOT/integration_tests"

_run "runtime inspector" "$PYTHON" -c "
import json, subprocess, sys
proc = subprocess.run(
    [sys.executable, '$ROOT/examples/runtime_inspector.py', '--format', 'json', '--timeout-ms', '30000'],
    capture_output=True, text=True, env=dict(__import__('os').environ, PYTHONPATH='$ROOT/src'),
)
if proc.returncode != 0:
    print(proc.stderr or proc.stdout)
    sys.exit(1)
d = json.loads(proc.stdout)
status = d.get('system_summary', {}).get('status')
checks = d.get('retrieval', {}).get('checks', [])
failed = [c['name'] for c in checks if not c.get('passed')]
if status != 'pass' or failed:
    print('inspector status:', status, 'failed checks:', failed)
    sys.exit(1)
print('inspector status: pass, checks:', len(checks))
"

_run "morning CLI status" "$PYTHON" -c "
import json, subprocess, sys
proc = subprocess.run(
    ['$ROOT/bin/morning-intelligence.sh', 'status'],
    capture_output=True, text=True, check=False,
)
if proc.returncode != 0:
    print(proc.stderr or proc.stdout)
    sys.exit(1)
data = json.loads(proc.stdout)
arts = data.get('artifacts', {})
if not all(arts.get(k) for k in ('latest.html', 'latest.json', 'latest.md')):
    print('missing artifacts:', arts)
    sys.exit(1)
print('artifacts:', arts)
"

if [[ "${VERIFY_FULL:-}" == "1" ]]; then
  _run "phase 5.1 certification" "$PYTHON" "$ROOT/examples/certify_phase51_runtime.py"
fi

echo ""
echo "========================================"
echo "  KNOWLEDGE_SERVICE VERIFICATION REPORT"
echo "========================================"
for line in "${REPORT[@]}"; do
  echo "  $line"
done
if [[ -n "$SKIPS" ]]; then
  echo ""
  echo "  SKIPPED (expected): $SKIPS"
  echo "  (SearXNG zero-result skips are environment-dependent)"
fi
echo ""
if [[ $FAILURES -eq 0 ]]; then
  echo "  RESULT: PASS"
  exit 0
else
  echo "  RESULT: FAIL ($FAILURES step(s))"
  exit 1
fi