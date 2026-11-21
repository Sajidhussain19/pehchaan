"""
app/main.py — the FastAPI web application for Pehchaan.

WHAT: Creates the FastAPI `app` object and defines its HTTP endpoints.
      For now there is only GET /health.
WHY:  Every later feature (correct a transcript, extract an action, the demo page)
      becomes an endpoint here. /health is the simplest possible endpoint. It proves the
      server runs, and it is what AWS or a load balancer pings to check the app is alive.

Run it with:
    uvicorn app.main:app --reload
    (meaning: in module `app.main`, serve the object named `app`)
"""

from fastapi import FastAPI

from app.config import settings

# Create the application. The title and description appear on the
# auto-generated docs page at http://127.0.0.1:8000/docs
app = FastAPI(
    title=settings.project_name,
    description="Pehchaan — gets Indian names right. A correction layer for speech-to-text.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    """Health check: confirms the server is running.

    It touches no OpenAI or database, so it stays fast and always works.
    FastAPI turns the returned Python dict into JSON automatically.
    """
    return {"status": "ok", "project": settings.project_name}
