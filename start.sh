#!/usr/bin/env bash
set -e

# Add standard Python & Render venv paths to PATH
export PATH="/opt/render/project/src/.venv/bin:/usr/local/bin:/usr/bin:$PATH"

# Activate Render's virtual environment if present
if [ -f "/opt/render/project/src/.venv/bin/activate" ]; then
    source /opt/render/project/src/.venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Locate python runtime
PYTHON_CMD="python"
if [ -f "/opt/render/project/src/.venv/bin/python" ]; then
    PYTHON_CMD="/opt/render/project/src/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
fi

echo "=== Running Database Migrations & Seeds on Startup ==="
$PYTHON_CMD -m alembic upgrade head || true
$PYTHON_CMD -m scripts.load_real_roster || true
$PYTHON_CMD -m scripts.import_ashtapradhan_questions || true
$PYTHON_CMD -m scripts.seed_ashtapradhan_roster || true
$PYTHON_CMD scripts/seed_admins.py || true
$PYTHON_CMD -m scripts.seed_department_assessments || true

# Locate and launch uvicorn
if [ -f "/opt/render/project/src/.venv/bin/uvicorn" ]; then
    exec /opt/render/project/src/.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
elif command -v uvicorn >/dev/null 2>&1; then
    exec uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
elif command -v python >/dev/null 2>&1; then
    exec python -m uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
else
    echo "ERROR: Could not locate uvicorn or python runtime."
    exit 1
fi
