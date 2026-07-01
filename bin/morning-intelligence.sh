#!/bin/zsh
set -u

KNOWLEDGE_SERVICE="${KNOWLEDGE_SERVICE:-/Users/sterlingdigital/Knowledge_Service}"
cd "$KNOWLEDGE_SERVICE" || exit 1

if [[ -x "$KNOWLEDGE_SERVICE/.venv/bin/python3" ]]; then
  PYTHON="$KNOWLEDGE_SERVICE/.venv/bin/python3"
else
  PYTHON="python3"
fi

export PYTHONPATH="$KNOWLEDGE_SERVICE/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m knowledge_service.production.morning "$@"