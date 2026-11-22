"""
app/api/routes.py — the HTTP endpoints of Pehchaan (Module 9).

WHAT: GET  /api/books                     contact books with a one-line description
      GET  /api/clips                     demo clips (held-out) first, then dev clips, with audio URLs
      GET  /audio/{variant}/{clip_id}.wav serves one clip's audio (ids validated, no path traversal)
      POST /api/process                   audio upload OR clip_id + variant OR plain text -> Pehchaan
                                          -> reminder or pending question (+ baseline (c) if compare=true)
      POST /api/clarify/{pending_id}      {entity_id, remember: "this_time" | "always"} -> reminder
      POST /api/preferences/reset?book=B  forget what a book learned (for repeated demos)
      GET  /api/reminders, GET /api/reminders/{id}, DELETE /api/reminders
      GET  /api/metrics                   summary of the FINAL held-out test report (for the scoreboard)
      GET  /api/config                    what the page needs to know (demo key required? limits)
      Guards (Module 10, app/api/guard.py): per-IP rate limit and a daily OpenAI budget on /api/process.
WHY:  This is what the demo page (Module 10) and the demo script talk to. Each endpoint only checks its
      inputs and calls app/api/flow.py, so the logic stays testable without HTTP.
"""

import json
import time
from functools import lru_cache
from typing import Literal
from uuid import UUID

import anyio
import openai
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path as PathParam, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api import audio as audio_io
from app.api import flow, guard
from app.config import settings
from app.decide.config import VERSION
from app.eval.decision import Decision
from app.eval.metrics import clip_outcome
from app.eval.runs import load_decision_objects, load_transcripts
from app.testset.validate import load_realspeech, load_testset
from app.kb.loader import DEFAULT_BOOK, available_books
from app.stt.baseline import RESULTS_DIR
from app.stt.transcribe import get_client, transcribe_live
from app.store import preferences as preference_store
from app.store import reminders as reminder_store

router = APIRouter()


class _LazyOpenAI:
    """Creates the real OpenAI client only when an API call is actually made.

    Passing a client object (instead of None) also tells Pehchaan's LLM fallback NOT to read or write the
    evaluation cache (data/results/pehchaan_llm_cache.json): live requests are always live.
    """

    def __getattr__(self, name):
        return getattr(get_client(), name)


def openai_client():
    """FastAPI dependency: tests replace it with a fake client (app.dependency_overrides)."""
    return _LazyOpenAI()


# How each evaluation outcome is said on screen (in words, never colour alone).
VERDICT_WORDS = {"ok": "✓ Correct", "wrong_target": "✗ Wrong target", "missed_clarification": "✗ Should have asked",
                 "unnecessary_question": "✗ Asked when it didn't need to",
                 "over_corrected": "✗ Changed a name that should stay", "wrong_behaviour": "✗ Wrong decision",
                 "wrong_action": "✗ Reminder details wrong", "entity_miss": "~ Right decision, name not fixed in text"}


@lru_cache(maxsize=1)
def _ground_truth() -> dict:
    gt = {s.id: s for s in load_testset(splits=None)}  # incl. test-2, so its demo clips get verdicts too
    gt.update({c.id: c for c in load_realspeech()})
    return gt


def _verdict(gt, decision: dict | None) -> dict | None:
    """Score one system on one clip with the SAME function the evaluation uses (app/eval/metrics.py)."""
    if gt is None or decision is None:
        return None
    outcome = clip_outcome(gt, decision["output_transcript"], Decision.model_validate(decision))
    return {"outcome": outcome, "label": VERDICT_WORDS.get(outcome, outcome), "ok": outcome == "ok"}


def visitor_id(request: Request) -> str:
    """An anonymous browser's UUID is its bearer credential for its own demo items."""
    raw = request.headers.get("x-visitor-id", "")
    try:
        value = UUID(raw)
        if value.version == 4 and str(value) == raw.lower():
            return str(value)
    except ValueError:
        pass
    raise HTTPException(400, "X-Visitor-Id must be a valid random UUID (v4)")


def _check_book(book: str) -> str:
    if book not in available_books():
        raise HTTPException(404, f"unknown contact book {book!r}; available: {', '.join(available_books())}")
    return book


@router.get("/api/books")
def books() -> list[dict]:
    return [{"book": name, "description": desc} for name, desc in available_books().items()]


@router.get("/api/clips")
def clips() -> list[dict]:
    return audio_io.list_clips()


@router.get("/audio/{variant}/{clip_id}.wav")
def clip_audio(variant: str = PathParam(pattern=r"^(clean|phone|real)$"),
               clip_id: str = PathParam(pattern=r"^[sr]\d{3}$")):
    try:
        return FileResponse(audio_io.clip_audio_path(variant, clip_id), media_type="audio/wav")
    except audio_io.AudioError as exc:
        raise HTTPException(exc.status, str(exc)) from exc


@router.get("/api/config")
def config() -> dict:
    return {"demo_key_required": settings.demo_key is not None, "daily_budget_usd": settings.daily_budget_usd,
            "rate_limit": f"{settings.rate_limit_requests} per {settings.rate_limit_window_seconds // 60} min",
            "max_upload_mb": audio_io.MAX_UPLOAD_BYTES // (1024 * 1024), "max_seconds": audio_io.MAX_SECONDS}


@router.post("/api/process")
def process(request: Request, file: UploadFile | None = File(None), clip_id: str | None = Form(None),
            variant: Literal["clean", "phone", "real"] = Form("clean"), text: str | None = Form(None),
            book: str = Form(DEFAULT_BOOK), compare: bool = Form(False), live_stt: bool = Form(False),
            live_baseline: bool = Form(False),
            direction: Literal["outgoing", "incoming"] | None = Form(None), caller_contact_id: str | None = Form(None),
            owner: str = Depends(visitor_id), client=Depends(openai_client)) -> dict:
    """Exactly one input: an uploaded recording, a clip (clip_id + variant), or plain text."""
    _check_book(book)
    given = [name for name, v in (("file", file), ("clip_id", clip_id), ("text", text)) if v]
    if len(given) != 1:
        raise HTTPException(422, "send exactly one input: an audio file, a clip_id (+ variant), or text")
    guard.check_rate(request)  # 429 if this visitor sent too many requests recently
    replay = bool(clip_id and book == DEFAULT_BOOK and not live_stt and direction is None and caller_contact_id is None)
    if not replay or (compare and live_baseline):
        guard.check_budget()
    t_start = time.perf_counter()
    stt = {"stt_ms": 0.0, "stt_cost_usd": 0.0, "stt_source": "typed sentence"}
    direction_used, caller = direction or "outgoing", caller_contact_id
    clip = None

    if text is not None:
        transcript = text.strip()
        if not transcript or len(transcript) > 1000:
            raise HTTPException(400, "text must be 1 to 1000 characters")
    elif file is not None:
        data = file.file.read(audio_io.MAX_UPLOAD_BYTES + 1)  # never read more than the limit + 1 byte
        try:
            suffix, seconds = audio_io.check_upload(file.filename, data)
        except audio_io.AudioError as exc:
            raise HTTPException(exc.status, str(exc)) from exc
        transcript, stt = _speech_to_text(data, suffix, seconds)
    else:
        try:
            clip = audio_io.clip_info(variant, clip_id)
            path = audio_io.clip_audio_path(variant, clip_id)
        except audio_io.AudioError as exc:
            raise HTTPException(exc.status, str(exc)) from exc
        if direction is None:  # use the clip's own call context, exactly as in the evaluation
            direction_used = clip.get("direction", "outgoing")
        if caller is None:
            caller = clip.get("caller_contact_id")
        saved = None if live_stt else load_transcripts("plain", variant).get(clip_id)
        if saved is not None:  # the same Module 4 transcript the evaluation used: free and repeatable
            transcript = saved
            stt = {"stt_ms": 0.0, "stt_cost_usd": 0.0, "stt_source": "saved transcript"}
        elif replay:
            raise HTTPException(404, "No saved transcript for this recording")
        else:
            transcript, stt = _speech_to_text(path.read_bytes(), ".wav", clip.get("duration_seconds"))
    if not transcript:
        raise HTTPException(422, "speech-to-text heard nothing; please try again")

    saved_p = saved_c = None
    if replay:
        saved_p = load_decision_objects("pehchaan", variant, VERSION).get(clip_id)
        if saved_p is None:
            raise HTTPException(404, "No saved Pehchaan decision for this recording")
        if compare and not live_baseline:
            saved_c = load_decision_objects("llm_baseline", variant, "gpt-4o-mini").get(clip_id)
    live_compare = compare and (not replay or live_baseline)
    result = flow.process(transcript, visitor_id=owner, book=book, direction=direction_used, caller=caller,
                          client=client, preview=clip is not None, saved_decision=saved_p, compare=live_compare)
    if replay and compare and not live_compare and saved_c is None:
        result["baseline_error"] = "Strong AI has no saved answer for this recording."
    if saved_c is not None:
        result.update(baseline=saved_c.model_dump(), baseline_ms=saved_c.latency_ms, baseline_cost_usd=0.0)
    decision = result["decision"]
    gt = _ground_truth().get(clip_id) if clip is not None and book == DEFAULT_BOOK else None
    total_ms = (time.perf_counter() - t_start) * 1000
    cost = stt["stt_cost_usd"] + (0.0 if replay else decision["cost_usd"])
    guard.record_spend(cost + (result["baseline_cost_usd"] or 0))
    previous = load_decision_objects("pehchaan", variant, "v1").get(clip_id) if replay and clip_id == "s090" else None
    return {
        "v1_output": previous.output_transcript if previous else None,
        "input": given[0], "book": book, "clip": {"clip_id": clip_id, "variant": variant, "said": clip.get("text")}
        if clip else None, "direction": direction_used, "caller_contact_id": caller,
        "heard_transcript": transcript, "output_transcript": decision["output_transcript"],
        "spans": result["spans"], "decision": decision, "reminder": result["reminder"], "pending": result["pending"],
        "pehchaan_source": f"saved {VERSION} decision from the evaluation run" if replay else None,
        "decision_source": "saved evaluation replay" if replay else "live",
        "latency_scope": "decision only" if replay else "end to end",
        "baseline": result["baseline"],
        "baseline_error": result.get("baseline_error"),
        # True when Pehchaan's LLM step failed and it asked (or kept) instead of deciding.
        "ai_unavailable": any("AI unavailable" in e["reason"] for e in decision["entities"]),
        "baseline_source": None if not compare or result.get("baseline_error") else ("saved evaluation replay" if saved_c is not None else "live"),
        # Ground truth only for test-set clips on the evaluated (default) contact book.
        "expected": {"behaviour": gt.expected_behaviour,
                     "target_entity_id": getattr(getattr(gt, "expected_action", None), "target_entity_id", None)}
        if gt is not None else None,
        "verdict": {"pehchaan": _verdict(gt, decision),
                    "baseline": _verdict(gt, result["baseline"])} if gt is not None else None,
        "names": _names_for(book, decision, result["baseline"]),
        "timings": {"stt_ms": stt["stt_ms"], "pehchaan_ms": result["pehchaan_ms"], "store_ms": result["store_ms"],
                    "baseline_ms": result["baseline_ms"], "total_ms": round(total_ms, 1)},
        "stt_source": stt["stt_source"], "used_llm": decision["used_llm"],
        # Cost of the whole interaction up to the reminder: speech-to-text + Pehchaan (baseline listed apart).
        "cost_usd": round(cost, 6),
        "baseline_cost_usd": result["baseline_cost_usd"],
    }


def _names_for(book: str, *decisions: dict | None) -> dict:
    """{entity id: {name, role}} for every id the decisions mention, looked up in the same contact book,
    so the page can say "Dr. Subramanian (dentist)" instead of "person_028"."""
    from app.kb.loader import get_by_id, use_book
    ids = set()
    for d in decisions:
        if d:
            ids |= {e["resolved_entity_id"] for e in d["entities"] if e["resolved_entity_id"]}
            ids |= set(d["clarify_candidates"]) | {d["action"]["target_entity_id"], d["action"]["place_entity_id"]}
    out = {}
    with use_book(book):
        for eid in sorted(i for i in ids if i):
            e = get_by_id(eid)
            out[eid] = {"name": e.name, "role": flow.role_of(e)} if e else {"name": eid, "role": None}
    return out


def _speech_to_text(data: bytes, suffix: str, seconds: float | None) -> tuple[str, dict]:
    """Await cancellable live STT from FastAPI's synchronous request worker."""
    estimated_seconds = seconds if seconds is not None else audio_io.MAX_SECONDS
    try:
        out = anyio.from_thread.run(transcribe_live, data, suffix, estimated_seconds)
    except (openai.OpenAIError, RuntimeError, TimeoutError) as err:
        raise HTTPException(503, f"Speech-to-text is unavailable right now ({type(err).__name__}). "
                                 "Demo clips and typed sentences still work.") from err
    return out["text"], {"stt_ms": out["latency_ms"], "stt_cost_usd": out["cost_estimate_usd"],
                         "stt_source": f"live {out['model']}"}


class ClarifyAnswer(BaseModel):
    entity_id: str
    remember: Literal["this_time", "always"]


@router.post("/api/clarify/{pending_id}")
def clarify(answer: ClarifyAnswer, pending_id: str = PathParam(pattern=r"^[0-9a-f]{16}$"),
            owner: str = Depends(visitor_id), client=Depends(openai_client)) -> dict:
    started = time.perf_counter()
    guard.check_budget()
    try:
        result = flow.answer(pending_id, answer.entity_id, answer.remember, visitor_id=owner, client=client)
    except flow.FlowError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    d = result["decision"]
    guard.record_spend(d["cost_usd"])
    return {"decision_source": "live", "latency_scope": "end to end", "pending_id": pending_id, "remember": answer.remember, "saved_preference": result["saved_preference"],
            "heard_transcript": d["heard_transcript"], "output_transcript": d["output_transcript"],
            "spans": result["spans"], "decision": d, "reminder": result["reminder"], "pending": result["pending"],
            "timings": {"pehchaan_ms": result["pehchaan_ms"], "store_ms": result["store_ms"],
                        "total_ms": round((time.perf_counter() - started) * 1000, 1)},
            "used_llm": d["used_llm"], "cost_usd": d["cost_usd"]}


@router.post("/api/preferences/reset")
def reset_preferences(book: str = Query(...)) -> dict:
    _check_book(book)
    return {"book": book, "removed": preference_store.reset(book)}


@router.get("/api/reminders")
def list_reminders(owner: str = Depends(visitor_id)) -> list[dict]:
    return [flow.reminder_view(r) for r in reminder_store.list_all(owner)]


@router.get("/api/reminders/{reminder_id}")
def get_reminder(reminder_id: int, owner: str = Depends(visitor_id)) -> dict:
    r = reminder_store.get(reminder_id, owner)
    if r is None:
        raise HTTPException(404, f"no reminder {reminder_id}")
    return flow.reminder_view(r)


@router.delete("/api/reminders")
def delete_reminders(owner: str = Depends(visitor_id)) -> dict:
    return {"deleted": reminder_store.delete_all(owner)}


def _v2_summary(pick) -> dict | None:
    """The v2 fix on test-2: a SECOND held-out set, frozen (tag test2-frozen) before v2 ran on it."""
    path = RESULTS_DIR / "report_test2_FINAL.json"
    if not path.exists():
        return None
    r = json.loads(path.read_text(encoding="utf-8"))
    return {"label": "test-2: 45 new sentences x clean + phone = 90 clips, frozen (tag test2-frozen) before "
                     "Pehchaan v2 ran on it; run once",
            "overall": {s: pick(r["overall"][s]) for s in ("c", "v1", "v2") if s in r["overall"]},
            "win_tie_loss": r["comparison"]["counts"] if r.get("comparison") else None}


@router.get("/api/metrics")
def metrics() -> dict:
    """The FINAL held-out test numbers, (c) vs Pehchaan, with raw counts (for the UI scoreboard)."""
    path = RESULTS_DIR / "report_test_FINAL.json"
    if not path.exists():
        raise HTTPException(404, "the final test report has not been produced yet")
    report = json.loads(path.read_text(encoding="utf-8"))
    keep = ("wrong_target_rate", "missed_clarification_rate", "unnecessary_question_rate", "over_correction_rate",
            "exact_action_target_accuracy", "reference_resolution_accuracy", "entity_accuracy", "wer",
            "behaviour_accuracy", "time_accuracy", "no_llm_rate", "latency_ms_mean", "latency_ms_median",
            "cost_usd_mean")
    pick = lambda m: {k: m[k] for k in keep if k in m}  # noqa: E731
    # Latency is re-measured on every run. The slides and README quote the FIRST final run (tag final-eval-v1,
    # data/results/report_test_FINAL.json at that tag); the repeat (final-eval-v1.1) replayed cached LLM answers
    # and was faster. All scored metrics were identical in both runs; only these timings differ.
    first_run_latency = {"c": {"median": 1502.4, "mean": 1548.5}, "pehchaan": {"median": 10.9, "mean": 297.7}}
    return {"label": "Held-out TEST split, run once (tag final-eval-v1); repeated after one approved change with "
                     "identical scores (final-eval-v1.1)", "split": report["split"],
            "overall": {s: pick(report["overall"][s]) for s in ("c", "pehchaan")},
            "per_audio": {a: {s: pick(m[s]) for s in ("c", "pehchaan") if s in m}
                          for a, m in report["per_audio"].items()},
            "win_tie_loss": report["comparison"]["counts"] if report.get("comparison") else None,
            "latency_first_run": first_run_latency,
            "v2": _v2_summary(pick),
            "latency_note": "first final run; the repeat measured {:.0f} / {:.0f} ms".format(
                report["overall"]["pehchaan"]["latency_ms_median"], report["overall"]["pehchaan"]["latency_ms_mean"])}
