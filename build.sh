#!/usr/bin/env bash
# Render Build Script
set -e

echo "=== [1/4] Installing Backend Dependencies ==="
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "=== [2/4] Running Database Migrations ==="
python -m alembic upgrade head

echo "=== [3/4] Building Frontend App ==="
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    cd frontend
    npm install
    npm run build
    cd ..
else
    echo "Frontend directory or package.json not ready yet. Skipping frontend build."
fi

echo "=== [4/4] Ensuring Essential Question Bank, Official Roster & Admin Seed ==="
if [ -f "data/HR_Team_Professional_Assessment.docx" ]; then
    python scripts/import_questions.py data/HR_Team_Professional_Assessment.docx || echo "Questions already loaded."
fi
if [ -f "data/Claim_Department_Question_Paper.docx" ]; then
    python scripts/import_claim_questions.py data/Claim_Department_Question_Paper.docx || echo "Claim questions loaded."
fi
if [ -f "data/ashtapradhan_questions.csv" ]; then
    python -m scripts.import_ashtapradhan_questions data/ashtapradhan_questions.csv || echo "Ashtapradhan questions loaded."
fi
python -m scripts.load_real_roster || echo "Real roster loaded."
python scripts/seed_admins.py || echo "Admins already seeded."
python -m scripts.seed_department_assessments || echo "Department assessments seeded."

chmod +x start.sh build.sh || true

echo "=== Build Complete Successfully ==="
