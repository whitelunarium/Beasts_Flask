#!/bin/bash
# scripts/setup.sh
# Run this once to set up your local BB_Flask2 development environment.
# Usage: cd /Users/samarthvaka/BB_Flask2 && bash scripts/setup.sh

set -e  # exit on any error

echo "=== BB_Flask2 Setup ==="
cd "$(dirname "$0")/.."

# ── 1. Python venv ───────────────────────────────────────────────────────────
echo ""
echo "[1/4] Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "      venv created."
else
    echo "      venv already exists, skipping."
fi

# ── 2. Install dependencies ──────────────────────────────────────────────────
echo ""
echo "[2/4] Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "      Dependencies installed."

# ── 3. Flask-Migrate init ────────────────────────────────────────────────────
echo ""
echo "[3/4] Initializing Flask-Migrate..."
if [ ! -d "migrations" ]; then
    flask db init
    flask db migrate -m "initial schema"
    flask db upgrade
    echo "      Migrations initialized and applied."
else
    echo "      migrations/ already exists, running upgrade..."
    flask db upgrade
fi

# ── 4. Seed the database ─────────────────────────────────────────────────────
echo ""
echo "[4/4] Seeding the database..."
python3 scripts/seed_db.py
echo "      Database seeded."

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To start the dev server:"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo ""
echo "API will be available at http://localhost:8425"
