"""
tests/conftest.py — shared pytest setup.

WHY: the per-IP rate limiter (app/api/guard.py) remembers requests in memory. Without a reset, many API
     tests in a row would hit the limit and fail with 429. Each test starts with a clean limiter.
"""

import pytest

from app.api import guard


@pytest.fixture(autouse=True)
def _fresh_rate_limiter():
    guard.reset_rate_limits()
    yield
    guard.reset_rate_limits()
