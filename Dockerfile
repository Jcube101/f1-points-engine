# ─── Stage 1: Build the React frontend ────────────────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./
RUN npm run build
# Output: /app/frontend/dist/

# ─── Stage 2: Python backend + built frontend ──────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built React app from stage 1
# FastAPI's StaticFiles mount expects: <repo_root>/frontend/dist/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# Expose Railway's dynamic port (Railway sets $PORT at runtime)
EXPOSE 8000

# Seed the DB then start the server.
# Railway sets PORT; fall back to 8000 for local `docker run` testing.
CMD ["sh", "-c", "python backend/seed.py && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
