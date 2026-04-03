FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source into backend/ so that all `from backend.X import Y`
# statements resolve correctly with /app on the Python path.
# This mirrors the root Dockerfile (used for Railway/Render production) and
# ensures docker-compose and direct `docker run` both work identically.
COPY . ./backend/

# Add /app to PYTHONPATH so `backend` is importable as a package
ENV PYTHONPATH=/app

EXPOSE 8000

# Seed the DB then start the server.
# Running as `python backend/seed.py` (not `python seed.py`) keeps imports
# consistent with PYTHONPATH and the root Dockerfile.
CMD ["sh", "-c", "python backend/seed.py && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
