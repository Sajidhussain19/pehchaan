"""
app/api/audio.py — safe handling of audio: browser uploads, test-set clips, and the files we serve.

WHAT: - check_upload(): accepts a browser-mic recording (webm / ogg / wav / mp3 / m4a) only if it is small
        (<= 5 MB), really is audio of that kind (checked by its first bytes, not just its name), and is
        short (<= 30 s). Returns the bytes, the file suffix and the duration.
      - clip_audio_path(): turns (variant, clip_id) into a file path ONLY through the manifests, after
        checking the id's format, so a request like "../../.env" can never reach another file.
      - list_clips(): the demo clips (demo_candidates.json first) and the dev clips, for GET /api/clips.
WHY:  The API is reachable from a browser, so every input is untrusted. Size and length limits also cap
      what one request can cost on the speech-to-text API.

Duration check: WAV, OGG, MP3 (and FLAC) are decoded by soundfile, so their exact length is checked.
WebM and M4A (what Chrome/Safari record) can't be read without ffmpeg, which we don't install. For those we
use an upper bound from the size: 30 s of browser speech at a generous 256 kbit/s is under 1 MB, so a bigger
WebM/M4A file is rejected as "probably longer than 30 s". The demo page also stops recording at 30 s.
"""

import io
import json
import re
from functools import lru_cache
from pathlib import Path

import soundfile as sf

from app.config import PROJECT_ROOT
from app.stt.baseline import RESULTS_DIR

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_SECONDS = 30.0
MAX_COMPRESSED_BYTES = 1_000_000  # webm/m4a: ~30 s at 256 kbit/s (see the note above)
SUFFIXES = (".webm", ".ogg", ".wav", ".mp3", ".m4a")
VARIANTS = ("clean", "phone", "real")
CLIP_ID = {"clean": re.compile(r"^s\d{3}$"), "phone": re.compile(r"^s\d{3}$"), "real": re.compile(r"^r\d{3}$")}
DATA_DIR = PROJECT_ROOT / "data"


class AudioError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _sniff(data: bytes) -> str | None:
    """The real audio type from the file's first bytes ("magic numbers")."""
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return ".wav"
    if data[:4] == b"OggS":
        return ".ogg"
    if data[:4] == b"\x1a\x45\xdf\xa3":  # EBML header: WebM / Matroska
        return ".webm"
    if data[4:8] == b"ftyp":  # MP4 container: m4a / mp4 audio
        return ".m4a"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return ".mp3"
    return None


def check_upload(filename: str | None, data: bytes) -> tuple[str, float | None]:
    """Validate an uploaded recording. Returns (suffix, duration in seconds or None if not decodable)."""
    if not data:
        raise AudioError("the uploaded file is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise AudioError(f"file too large: {len(data) / 1e6:.1f} MB (limit {MAX_UPLOAD_BYTES / 1e6:.0f} MB)", 413)
    claimed = Path(filename or "").suffix.lower()
    real = _sniff(data)
    if real is None:
        raise AudioError(f"not a supported audio file; send one of {', '.join(SUFFIXES)}", 415)
    if claimed and claimed in SUFFIXES and claimed != real and {claimed, real} != {".ogg", ".webm"}:
        raise AudioError(f"the file is named {claimed} but its content is {real}", 415)
    if real in (".webm", ".m4a"):
        if len(data) > MAX_COMPRESSED_BYTES:
            raise AudioError(f"recording probably longer than {MAX_SECONDS:.0f} s "
                             f"({len(data) / 1e6:.1f} MB of {real[1:]}); please keep it under {MAX_SECONDS:.0f} s")
        return real, None
    try:
        info = sf.info(io.BytesIO(data))
    except Exception as exc:  # soundfile raises its own error types for broken files
        raise AudioError(f"could not read the audio ({real[1:]}): {exc}") from exc
    seconds = info.frames / info.samplerate if info.samplerate else 0.0
    if seconds > MAX_SECONDS:
        raise AudioError(f"recording is {seconds:.1f} s long; the limit is {MAX_SECONDS:.0f} s")
    return real, seconds


@lru_cache(maxsize=1)
def _manifests() -> dict:
    """{variant: {clip_id: {...}}} read from the test-set and real-speech manifests."""
    synth = json.loads((DATA_DIR / "testset" / "manifest.json").read_text(encoding="utf-8"))
    real_path = DATA_DIR / "realspeech" / "manifest.json"
    real = json.loads(real_path.read_text(encoding="utf-8")) if real_path.exists() else []
    return {"clean": {c["id"]: {**c, "path": c["clean_path"]} for c in synth},
            "phone": {c["id"]: {**c, "path": c["phone_path"]} for c in synth},
            "real": {c["id"]: {**c, "path": c["audio_path"]} for c in real}}


def clip_info(variant: str, clip_id: str) -> dict:
    """The manifest entry of one clip, after strict checks of both values."""
    if variant not in VARIANTS:
        raise AudioError(f"variant must be one of {', '.join(VARIANTS)}", 404)
    if not CLIP_ID[variant].match(clip_id or ""):
        raise AudioError("invalid clip id", 404)
    info = _manifests()[variant].get(clip_id)
    if info is None:
        raise AudioError(f"no {variant} clip {clip_id}", 404)
    return info


def clip_audio_path(variant: str, clip_id: str) -> Path:
    """The WAV file of a clip. The path comes from the manifest, and must stay inside data/."""
    path = (PROJECT_ROOT / clip_info(variant, clip_id)["path"]).resolve()
    if not path.is_relative_to(DATA_DIR.resolve()) or path.suffix != ".wav" or not path.is_file():
        raise AudioError("audio file not available", 404)
    return path


# The clips the presenter rehearsed with (original held-out test set). Since v2 they are "seen": v2's fixes were
# designed after looking at v1's failures on that set, so the group label says so.
REHEARSED = [("s104", "missed clarification — Rohit vs Rohith"),
             ("s140", "clue vs default — tooth → dentist"),
             ("s067", "misheard name — Bhagyalakshmi Jewellers, Panjagutta"),
             ("s090", None)]  # label computed from the saved v2 results (see _s090_label)
GROUP_SEEN = "Original test set (seen before v2)"
GROUP_TEST2 = "Held-out test-2 (v2)"


def _v2_ok_on_both_audios(clip_id: str) -> bool:
    """Scored from the SAVED v2 decisions with the evaluation's own function (app/eval/metrics.clip_outcome)."""
    from app.decide.config import VERSION
    from app.eval.decision import Decision
    from app.eval.metrics import clip_outcome
    from app.testset.validate import load_testset
    gt = {s.id: s for s in load_testset(splits=None)}[clip_id]
    for audio in ("clean", "phone"):
        path = RESULTS_DIR / f"pehchaan_{audio}_{VERSION}.json"
        saved = json.loads(path.read_text(encoding="utf-8"))["clips"].get(clip_id) if path.exists() else None
        if saved is None or clip_outcome(gt, saved["output_transcript"], Decision.model_validate(saved)) != "ok":
            return False
    return True


def _s090_label() -> tuple[str, bool]:
    """s090 ("ee roju" -> Dr. Raju) was v1's known failure. (label, still_a_failure)."""
    if _v2_ok_on_both_audios("s090"):
        return "v1 failure — fixed in v2", False
    return "Known failure", True


def list_clips() -> list[dict]:
    """Rehearsed clips (original test set, seen) first, then the test-2 demo clips, then every dev clip."""
    out, seen = [], set()
    texts = {c["id"]: c for c in _manifests()["clean"].values()}
    for cid, label in REHEARSED:
        failure = False
        if label is None:
            label, failure = _s090_label()
        c = texts[cid]
        out.append({"clip_id": cid, "group": GROUP_SEEN, "text": c["text"], "category": c["category"],
                    "demo_kind": label, "label": label, "honest_failure": failure,
                    "fixed_in_v2": cid == "s090" and not failure,
                    "audio": {v: f"/audio/{v}/{cid}.wav" for v in ("clean", "phone")}})
        seen.add(cid)
    demo_path = RESULTS_DIR / "demo_candidates.json"
    for d in json.loads(demo_path.read_text(encoding="utf-8")) if demo_path.exists() else []:
        label = "Known failure (v2)" if d["honest_failure"] else d["kind"]
        out.append({"clip_id": d["clip_id"], "group": GROUP_TEST2, "text": d["text"],
                    "category": d["category"], "demo_kind": label, "label": label, "honest_failure": d["honest_failure"],
                    "audio": {v: f"/audio/{v}/{d['clip_id']}.wav" for v in ("clean", "phone")}})
        seen.add(d["clip_id"])
    for variant_set, variants in (("clean", ("clean", "phone")), ("real", ("real",))):
        for cid, c in sorted(_manifests()[variant_set].items()):
            # Real-speech audio is not in git; only offer clips whose audio was fetched on this machine.
            if variant_set == "real" and not (PROJECT_ROOT / c["path"]).is_file():
                continue
            if c["split"] == "dev" and cid not in seen:
                out.append({"clip_id": cid, "group": "Dev clips", "text": c["text"], "category": c["category"],
                            "audio": {v: f"/audio/{v}/{cid}.wav" for v in variants},
                            **({"source": "AI4Bharat Svarah (CC BY 4.0)"} if variant_set == "real" else {})})
    return out
