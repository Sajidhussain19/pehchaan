"""
app/api/guard.py — protects the public demo: rate limit, daily OpenAI budget, demo key, own-origin only.

WHAT: - check_rate(request): at most RATE_LIMIT_REQUESTS calls to POST /api/process per client IP per
        RATE_LIMIT_WINDOW_SECONDS (default 20 per 10 minutes). Kept in memory: a restart resets it, fine for a demo.
      - check_budget() / record_spend(usd): today's OpenAI spend is stored in SQLite (table `spend`, one row per
        UTC day). Before a request we check there is room for its worst case; after it, we add what it cost.
      - security_middleware: for every request that CHANGES something under /api (POST, DELETE):
          * if the browser sends an Origin header, it must be our own origin (or one in ALLOWED_ORIGINS),
            so another website can't make a visitor's browser use our demo (and our OpenAI budget);
          * if DEMO_KEY is set, the X-Demo-Key header must match it.
WHY:  A public link + a paid API = anyone could run up the bill. These are the simplest guards that work:
      a polite "slow down" per visitor, a hard daily ceiling for everyone, and an optional password.
"""

import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.store.db import connect

# Worst case of one /api/process call: 30 s of speech-to-text (~$0.0015) + baseline (c) (~$0.0015)
# + Pehchaan's small LLM fallback (~$0.0003), rounded up. We only start a request if this much is left.
WORST_CASE_REQUEST_USD = 0.005

_hits: dict[str, deque] = defaultdict(deque)  # client IP -> times of its recent requests
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    """The visitor's IP. Behind CloudFront (TRUST_PROXY=true) it is the LAST address in X-Forwarded-For:
    CloudFront appends the address it really saw, after anything the visitor sent. Taking the first one would
    let a visitor fake a new IP for every request and dodge the rate limit."""
    if settings.trust_proxy and (fwd := request.headers.get("x-forwarded-for")):
        return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def check_rate(request: Request) -> None:
    """Sliding window: forget hits older than the window, then refuse if the window is full."""
    ip, now = client_ip(request), time.monotonic()
    with _lock:
        hits = _hits[ip]
        while hits and now - hits[0] > settings.rate_limit_window_seconds:
            hits.popleft()
        if len(hits) >= settings.rate_limit_requests:
            wait = int(settings.rate_limit_window_seconds - (now - hits[0])) + 1
            raise HTTPException(429, f"Too many requests from your connection: the demo allows "
                                     f"{settings.rate_limit_requests} per {settings.rate_limit_window_seconds // 60} "
                                     f"minutes. Please try again in {wait} s.")
        hits.append(now)


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def spent_today() -> float:
    with connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS spend (day TEXT PRIMARY KEY, usd REAL NOT NULL DEFAULT 0)")
        row = conn.execute("SELECT usd FROM spend WHERE day = ?", (_today(),)).fetchone()
    return row["usd"] if row else 0.0


def check_budget() -> None:
    """Refuse (503) when today's spend plus one worst-case request would pass DAILY_BUDGET_USD."""
    spent = spent_today()
    if spent + WORST_CASE_REQUEST_USD > settings.daily_budget_usd:
        raise HTTPException(503, f"The demo's daily AI budget (${settings.daily_budget_usd:.2f}) is used up "
                                 f"(${spent:.2f} spent today, UTC). Typed sentences that need no AI still work "
                                 "tomorrow; the recorded demo video shows everything.")


def record_spend(usd: float) -> None:
    """Add what a request actually cost (speech-to-text + Pehchaan's LLM + baseline (c))."""
    if not usd:
        return
    with connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS spend (day TEXT PRIMARY KEY, usd REAL NOT NULL DEFAULT 0)")
        conn.execute("INSERT INTO spend (day, usd) VALUES (?, ?) ON CONFLICT(day) DO UPDATE SET usd = usd + ?",
                     (_today(), usd, usd))


def allowed_origins(request: Request) -> set[str]:
    own = {f"{request.url.scheme}://{request.url.netloc}"}
    if settings.trust_proxy and (host := request.headers.get("x-forwarded-host")):
        own.add(f"{request.headers.get('x-forwarded-proto', 'https')}://{host}")
    return own | {o.strip().rstrip("/") for o in settings.allowed_origins.split(",") if o.strip()}


async def security_middleware(request: Request, call_next):
    """Runs before every request. Only requests that change something under /api are checked."""
    if request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD", "OPTIONS"):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in allowed_origins(request):
            return JSONResponse({"detail": f"requests from {origin} are not allowed"}, status_code=403)
        if settings.demo_key is not None:
            sent = request.headers.get("x-demo-key", "")
            # compare_digest takes the same time for any wrong key, so the key can't be guessed by timing.
            if not secrets.compare_digest(sent.encode(), settings.demo_key.get_secret_value().encode()):
                return JSONResponse({"detail": "this demo needs the demo key (ask the presenter)"}, status_code=401)
    return await call_next(request)
