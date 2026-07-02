#!/bin/zsh
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KNOWLEDGE_SERVICE="${KNOWLEDGE_SERVICE:-$(cd "$SCRIPT_DIR/.." && pwd)}"
cd "$KNOWLEDGE_SERVICE" || exit 1

if [[ -x "$KNOWLEDGE_SERVICE/.venv/bin/python3" ]]; then
  PYTHON="$KNOWLEDGE_SERVICE/.venv/bin/python3"
else
  PYTHON="python3"
fi

export PYTHONPATH="$KNOWLEDGE_SERVICE/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m knowledge_service.production.morning "$@"