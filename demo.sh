#!/usr/bin/env bash
# ESG+SCRM Demo Setup — run this once to install dependencies

set -e

DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DEMO_DIR"

echo "=== ESG+SCRM Investor Demo Setup ==="

# Backend
echo ""
echo "[1/3] Setting up Python backend..."
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet fastapi uvicorn python-multipart 2>/dev/null || pip install fastapi uvicorn python-multipart

# Frontend
echo ""
echo "[2/3] Setting up React frontend..."
cd apps/web
npm install --silent 2>/dev/null || npm install
cd ../..

echo ""
echo "[3/3] Done."
echo ""
echo "=== TO RUN THE DEMO ==="
echo ""
echo "Terminal 1 — Backend:"
echo "  source .venv/bin/activate"
echo "  python -m uvicorn src.api.main:app --reload --port 8000"
echo ""
echo "Terminal 2 — Frontend:"
echo "  cd apps/web"
echo "  npm run dev"
echo ""
echo "Then open: http://localhost:5173"
echo ""
