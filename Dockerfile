# Dockerfile — packages Pehchaan (API + demo page) as one container (Module 10).
#
# WHAT: Python 3.12 slim + our pinned requirements + the project files, run by uvicorn on port 8000
#       as a NON-ROOT user. Runtime state (reminders DB, learned preferences) goes to /app/state,
#       which you mount as a volume so it survives restarts.
# WHY:  The same image runs on a laptop and on EC2. The OpenAI key is NOT in the image: pass it at run time
#       with --env-file (see DEPLOY.md). .dockerignore keeps .env, venv and caches out of the build.
#
# Build and run locally:
#   docker build -t pehchaan .
#   docker run --rm -p 8000:8000 --env-file .env -v pehchaan-state:/app/state pehchaan
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STATE_DIR=/app/state

WORKDIR /app

# Dependencies first: this layer is cached and only rebuilt when requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# A normal user without admin rights: if the app were ever compromised, it can't change the system.
RUN useradd --create-home --uid 10001 pehchaan && mkdir -p /app/state && chown pehchaan:pehchaan /app/state
COPY --chown=pehchaan:pehchaan . .
USER pehchaan

EXPOSE 8000
# Container health: Docker marks the container unhealthy if /health stops answering.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
# --proxy-headers: behind CloudFront, uvicorn reads the real scheme (https) from X-Forwarded-Proto.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
