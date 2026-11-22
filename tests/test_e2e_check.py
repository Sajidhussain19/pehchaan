"""The evaluator should pass a working demo and fail when a published result changes."""
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import routes
from app.config import settings
from app.kb import loader
from app.main import app
from app.store import db
from scripts import demo_flow, e2e_check
from tests.test_api import FakeOpenAI, mock_live_stt


@pytest.fixture
def judge(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)
    monkeypatch.setattr(settings, "demo_key", None)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(loader, "RUNTIME_PREFS_DIR", tmp_path)
    monkeypatch.setattr(loader, "PREFERENCES_PATH", tmp_path / "default.json")
    with TestClient(app) as client:
        yield client


def test_judge_without_key(judge, capsys):
    assert e2e_check.verify(judge) == 0
    output = capsys.readouterr().out
    assert "ALL PASSED" in output and "2 skipped" in output
    assert "Pehchaan wrong_target / Strong AI ok" in output
    assert "Dr. Subramanian at 18:00" in output
    assert judge.get("/api/reminders").json() == []


def test_judge_with_configured_ai(judge, monkeypatch, capsys):
    fake = FakeOpenAI(heard="Call Rohit at 6 p.m.")
    monkeypatch.setattr(settings, "openai_api_key", SecretStr("unit-test-only"))
    monkeypatch.setitem(app.dependency_overrides, routes.openai_client, lambda: fake)
    mock_live_stt(monkeypatch, fake)
    assert e2e_check.verify(judge) == 0
    assert "0 skipped" in capsys.readouterr().out
    assert ("stt", settings.transcription_model) in fake.calls and ("chat", "decision") in fake.calls


def test_judge_reports_a_wrong_score_and_still_resets(judge, monkeypatch, capsys):
    actual = routes._v2_summary

    def wrong_score(pick):
        summary = actual(pick)
        summary["win_tie_loss"]["win"] = 0
        return summary

    monkeypatch.setattr(routes, "_v2_summary", wrong_score)
    assert e2e_check.verify(judge) == 1
    output = capsys.readouterr().out
    assert "FAIL     Scoreboard" in output and "1 failed" in output
    assert "PASS     Reset reminders and book B" in output


def test_standalone_doctor_demo_stores_the_advertised_time(judge, capsys):
    assert demo_flow.run(judge, compare=False) == 0
    assert "Dr. Venkataramana (family doctor), time=18:00" in capsys.readouterr().out
    rows = judge.get("/api/reminders").json()
    assert any(r["target_name"] == "Dr. Subramanian" and r["time"] == "18:00" for r in rows)
