"""
tests/test_health.py — automated test for the /health endpoint.

WHAT: Uses FastAPI's TestClient to call GET /health and checks the response.
WHY:  It is the smallest possible check that the app imports and serves requests.
      If a later module breaks app startup (a bad import, broken config), this test
      fails at once and points us to the problem.

Run with:  pytest -v
"""

from fastapi.testclient import TestClient

from app.main import app

# TestClient calls the app directly in memory. No real server or port is needed,
# so the test is fast and reliable.
client = TestClient(app)


def test_health_returns_ok():
    # Call the endpoint as a browser would.
    response = client.get("/health")

    # 200 is the HTTP status code for "OK".
    assert response.status_code == 200
    # The JSON body must match exactly.
    assert response.json() == {"status": "ok", "project": "Pehchaan"}
