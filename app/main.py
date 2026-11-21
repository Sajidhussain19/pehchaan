"""
app/main.py — the FastAPI web application for Pehchaan.

WHAT: Creates the FastAPI `app` object, defines GET /health, and plugs in the Pehchaan API
      (app/api/routes.py: process, clarify, reminders, books, clips, audio, metrics).
WHY:  This file stays small on purpose: the endpoints live in app/api/, the logic in app/api/flow.py. /health is the simplest possible endpoint. It proves the
      server runs, and it is what AWS or a load balancer pings to check the app is alive.

Run it with:
    uvicorn app.main:app --reload
    (meaning: in module `app.main`, serve the object named `app`)
"""

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings

# Create the application. The title and description appear on the
# auto-generated docs page at http://127.0.0.1:8000/docs
app = FastAPI(
    title=settings.project_name,
    description="Pehchaan — gets Indian names right. A correction layer for speech-to-text.",
    version="0.9.0",
)
app.include_router(router)  # every /api/... and /audio/... endpoint (Module 9)


@app.get("/health")
def health() -> dict:
    """Health check: confirms the server is running.

    It touches no OpenAI or database, so it stays fast and always works.
    FastAPI turns the returned Python dict into JSON automatically.
    """
    return {"status": "ok", "project": settings.project_name}
