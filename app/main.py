"""
app/main.py — the FastAPI web application for Pehchaan.

WHAT: Creates the FastAPI `app` object, defines GET /health, plugs in the Pehchaan API
      (app/api/routes.py: process, clarify, reminders, books, clips, audio, metrics), the demo guards
      (app/api/guard.py) and serves the demo page from web/ at "/" (Module 10).
WHY:  This file stays small on purpose: the endpoints live in app/api/, the logic in app/api/flow.py. /health is the simplest possible endpoint. It proves the
      server runs, and it is what AWS or a load balancer pings to check the app is alive.

Run it with:
    uvicorn app.main:app --reload
    (meaning: in module `app.main`, serve the object named `app`)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.guard import security_middleware
from app.api.routes import router
from app.config import PROJECT_ROOT, settings

# Create the application. The title and description appear on the
# auto-generated docs page at http://127.0.0.1:8000/docs
app = FastAPI(
    title=settings.project_name,
    description="Pehchaan — gets Indian names right. A correction layer for speech-to-text.",
    version="0.9.0",
)
app.include_router(router)  # every /api/... and /audio/... endpoint (Module 9)
# Same-origin by default: only origins listed in ALLOWED_ORIGINS may call the API from another site.
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type", "X-Demo-Key", "X-Visitor-Id"])
app.middleware("http")(security_middleware)  # own-origin check + optional demo key on changing requests


@app.get("/health")
def health() -> dict:
    """Health check: confirms the server is running.

    It touches no OpenAI or database, so it stays fast and always works.
    FastAPI turns the returned Python dict into JSON automatically.
    """
    return {"status": "ok", "project": settings.project_name}


# The demo page (web/index.html + app.js + style.css). Mounted LAST, so /api, /audio and /health win.
# html=True serves index.html for "/".
app.mount("/", StaticFiles(directory=PROJECT_ROOT / "web", html=True), name="web")
