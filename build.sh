#!/usr/bin/env bash
# build.sh — Production build script
#
# Mirrors what the Railway Dockerfile does, but runs natively (no Docker).
# Useful for testing the production build locally before deploying.
#
# Usage:
#   chmod +x build.sh && ./build.sh
#
# After running, the backend serves the full app at http://localhost:${PORT:-8000}

set -euo pipefail

echo "=== F1 Points Engine — Production Build ==="

# ── Step 1: Build the React frontend ─────────────────────────────────────────
echo ""
echo "→ Installing frontend dependencies..."
cd frontend
npm ci --silent

echo "→ Building React app (output: frontend/dist/)..."
npm run build
cd ..

# ── Step 2: Seed the database ─────────────────────────────────────────────────
echo ""
echo "→ Seeding database..."
python backend/seed.py

# ── Step 3: Start the backend (serves API + static React app) ─────────────────
PORT="${PORT:-8000}"
echo ""
echo "→ Starting FastAPI on port ${PORT}..."
echo "   Open http://localhost:${PORT} — the full app is live."
echo ""
uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
