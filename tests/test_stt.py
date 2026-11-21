"""
tests/test_stt.py — tests for speech-to-text, name hints and caching (Module 4).

WHAT: Checks that transcribe() returns the right shape and retries transient errors, that the
      hint prompt respects its size budget and puts contacts first, and that the baseline runner
      skips clips that are already transcribed.
WHY:  These tests use a FAKE OpenAI client, so they are free, fast and work offline. The real
      API is only called by scripts/run_baseline.py.

Run with:  pytest -v
"""

from types import SimpleNamespace

import httpx
import numpy as np
import openai
import pytest
import soundfile as sf

from app.kb.loader import get_by_type
from app.stt import baseline
from app.stt.hints import build_hint_prompt, estimate_tokens
from app.stt.transcribe import transcribe


class FakeTranscriptions:
    """Stands in for client.audio.transcriptions. Can fail N times before succeeding."""

    def __init__(self, text="hello world", fail_times=0):
        self.text, self.fail_times, self.calls = text, fail_times, []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) <= self.fail_times:
            raise openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com"))
        return SimpleNamespace(text=self.text + "  ")


def fake_client(**kwargs):
    transcriptions = FakeTranscriptions(**kwargs)
    return SimpleNamespace(audio=SimpleNamespace(transcriptions=transcriptions)), transcriptions


@pytest.fixture
def wav(tmp_path):
    """A real 2-second silent WAV file, so duration and cost can be computed."""
    path = tmp_path / "clip.wav"
    sf.write(path, np.zeros(16000 * 2, dtype=np.float32), 16000)
    return path


def test_transcribe_returns_expected_shape(wav):
    client, calls = fake_client(text="Call Dr. Raju")
    out = transcribe(wav, model="gpt-4o-mini-transcribe", client=client)
    assert set(out) == {"text", "model", "latency_ms", "cost_estimate_usd"}
    assert out["text"] == "Call Dr. Raju"  # surrounding spaces stripped
    assert out["model"] == "gpt-4o-mini-transcribe"
    assert out["cost_estimate_usd"] == pytest.approx(2 / 60 * 0.003, rel=1e-3)  # 2 seconds of audio
    assert "prompt" not in calls.calls[0]  # plain baseline sends no prompt


def test_transcribe_sends_prompt_when_given(wav):
    client, calls = fake_client()
    transcribe(wav, prompt="Names: Kukatpally.", model="gpt-4o-mini-transcribe", client=client)
    assert calls.calls[0]["prompt"] == "Names: Kukatpally."


def test_transcribe_retries_transient_errors_with_backoff(wav):
    client, calls = fake_client(fail_times=2)
    waits = []
    out = transcribe(wav, model="whisper-1", client=client, sleep=waits.append)
    assert out["text"] == "hello world"
    assert len(calls.calls) == 3 and waits == [1, 2]  # waited 1s, then 2s


def test_transcribe_gives_up_after_max_attempts(wav):
    client, _ = fake_client(fail_times=10)
    with pytest.raises(openai.APIConnectionError):
        transcribe(wav, model="whisper-1", client=client, sleep=lambda s: None, max_attempts=3)


def test_transcribe_rejects_unknown_model(wav):
    with pytest.raises(ValueError, match="unsupported model"):
        transcribe(wav, model="not-a-model", client=fake_client()[0])


def test_hints_respect_budget_and_put_contacts_first():
    hint = build_hint_prompt(budget_tokens=100)
    assert estimate_tokens(hint.text) <= 100
    assert hint.excluded_ids  # the KB does not fit in 100 tokens
    contact_ids = {e.id for e in get_by_type("person")}
    assert hint.included_ids[0] in contact_ids  # priority: contacts come first
    total = len(get_by_type("person")) + len(get_by_type("place")) + len(get_by_type("business"))
    assert len(hint.included_ids) + len(hint.excluded_ids) == total


def test_whisper_budget_is_small_but_gpt4o_fits_whole_kb():
    assert build_hint_prompt("whisper-1").summary()["excluded"] > 0  # 224 tokens can't hold the KB
    assert build_hint_prompt("gpt-4o-mini-transcribe").summary()["excluded"] == 0


def test_caching_skips_clips_already_transcribed(tmp_path):
    clips = [{"id": f"s00{i}", "split": "dev", "reference_text": "x", "audio_path": "a.wav",
              "duration_seconds": 1.0} for i in range(1, 4)]
    path = tmp_path / "results.json"
    results = {"meta": {}, "clips": {"s001": {"transcript": "already done"}}}
    called = []

    def fake_transcribe(audio_path, prompt=None):
        called.append(audio_path)
        return {"text": "new", "latency_ms": 1.0, "cost_estimate_usd": 0.0}

    n = baseline.run_clips(clips, results, path, fake_transcribe, workers=1)
    assert n == 2 and len(called) == 2  # s001 was skipped
    assert results["clips"]["s001"]["transcript"] == "already done"
    # A second run finds everything cached: nothing is transcribed.
    again = baseline.run_clips(clips, baseline.load_results(path), path, fake_transcribe, workers=1)
    assert again == 0 and len(called) == 2


def test_load_clips_reads_synthetic_manifest():
    clips = baseline.load_clips("phone", "dev")
    assert clips and all(c["split"] == "dev" and c["audio_path"].endswith(".wav") for c in clips)
