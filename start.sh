#!/usr/bin/env bash
set -e

# Activate Render's virtual environment if present
if [ -f "/opt/render/project/src/.venv/bin/activate" ]; then
    source /opt/render/project/src/.venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Detect python runtime and start uvicorn
if command -v python3 >/dev/null 2>&1; then
    exec python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
elif command -v python >/dev/null 2>&1; then
    exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
elif command -v uvicorn >/dev/null 2>&1; then
    exec uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
else
    echo "ERROR: Could not locate python3, python, or uvicorn runtime."
    exit 1
fi
