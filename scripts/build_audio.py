"""
scripts/build_audio.py — turns every test sentence into audio with OpenAI text-to-speech.

WHAT: For each sentence in data/testset/sentences.json it:
        1. asks OpenAI TTS to speak it (Indian English accent, conversational pace) and saves
           data/testset/audio/clean/{id}.wav
        2. makes a "phone quality" copy, data/testset/audio/phone/{id}.wav: 8 kHz, only the
           300-3400 Hz band a phone line carries, plus light background noise
      Then it writes data/testset/manifest.json, listing every clip with its voice, speed and duration.
WHY:  The track asks us to run "the same recordings" through a base model and through Pehchaan.
      These are those recordings, with known correct text. The phone copy matches what a call
      assistant like Equal AI's really hears: narrow-band, slightly noisy audio.

Run from the project root:
    python scripts/build_audio.py --limit 3      # first 3 clips only (cheap test)
    python scripts/build_audio.py                # everything; existing clips are skipped (free)
"""

import argparse
import io
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfiltfilt

# Make the project root importable when this file runs as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openai  # noqa: E402

from app.config import PROJECT_ROOT, settings  # noqa: E402
from app.testset.validate import load_testset  # noqa: E402

TESTSET_DIR = PROJECT_ROOT / "data" / "testset"
CLEAN_DIR = TESTSET_DIR / "audio" / "clean"
PHONE_DIR = TESTSET_DIR / "audio" / "phone"
MANIFEST_PATH = TESTSET_DIR / "manifest.json"

# Voices available on both gpt-4o-mini-tts and tts-1. We rotate through them so the test
# set doesn't depend on one speaker's voice.
VOICES = ["alloy", "ash", "coral", "echo", "nova", "onyx", "sage", "shimmer"]
# Small speed changes (1.0 = normal) so not every clip has the same pace.
SPEEDS = [0.95, 1.0, 1.05, 1.1]

# Style prompt for gpt-4o-mini-tts. tts-1 ignores style, so we don't send this to it.
INSTRUCTIONS = (
    "Speak in a natural Indian English accent, like a person on a phone call in Hyderabad. "
    "Conversational, relaxed pace. Pronounce Indian names and places the way a local would."
)

# Approximate public prices in US dollars, used only for the printed estimate.
# gpt-4o-mini-tts is billed by audio length (~$0.015 per minute of speech);
# tts-1 is billed by text length ($15 per 1M characters).
PRICE_PER_MINUTE_MINI_TTS = 0.015
PRICE_PER_CHAR_TTS1 = 15 / 1_000_000
CHARS_PER_SECOND = 14  # rough speaking rate, to turn text length into minutes

PHONE_RATE = 8000  # telephone sample rate (Hz)
NOISE_SNR_DB = 25  # signal-to-noise ratio: higher = quieter noise. 25 dB is a light hiss.


def estimate_cost(texts: list[str]) -> float:
    """Estimated dollars for these texts, using whichever model would be more expensive."""
    chars = sum(len(t) for t in texts)
    minutes = chars / CHARS_PER_SECOND / 60
    return max(minutes * PRICE_PER_MINUTE_MINI_TTS, chars * PRICE_PER_CHAR_TTS1)


def voice_and_speed(index: int) -> tuple[str, float]:
    """Deterministic choice from the sentence's position, so re-runs give the same answer
    (and the manifest stays correct for clips we skip)."""
    return VOICES[index % len(VOICES)], SPEEDS[(index // len(VOICES)) % len(SPEEDS)]


class TTS:
    """Small wrapper that tries the main model and switches to the fallback once if needed."""

    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key.get_secret_value())
        self.model = settings.tts_model
        self.chars = 0  # characters sent, for the final cost estimate

    def speak(self, text: str, voice: str, speed: float) -> bytes:
        try:
            return self._call(self.model, text, voice, speed)
        except (openai.NotFoundError, openai.PermissionDeniedError, openai.BadRequestError) as err:
            # Only switch models once, and only away from the main model.
            if self.model == settings.tts_fallback_model:
                raise
            print(f"  [WARN] {self.model} failed ({type(err).__name__}); switching to {settings.tts_fallback_model}")
            self.model = settings.tts_fallback_model
            return self._call(self.model, text, voice, speed)

    def _call(self, model: str, text: str, voice: str, speed: float) -> bytes:
        kwargs = dict(model=model, voice=voice, input=text, speed=speed, response_format="wav")
        if model != "tts-1" and model != "tts-1-hd":
            kwargs["instructions"] = INSTRUCTIONS  # only the newer model understands style prompts
        response = self.client.audio.speech.create(**kwargs)
        self.chars += len(text)
        return response.content  # raw WAV bytes


def make_phone_quality(audio: np.ndarray, rate: int, seed: int) -> np.ndarray:
    """Turn clean audio into something that sounds like a phone call.

    1. Resample to 8 kHz: phone lines carry only 8000 samples per second.
    2. Band-pass 300-3400 Hz: phones cut off deep bass and high treble.
    3. Add light white noise: real calls are never perfectly silent.
    """
    if audio.ndim > 1:  # stereo -> mono, just in case
        audio = audio.mean(axis=1)

    # resample_poly(x, up, down) changes the rate by up/down, with a built-in anti-aliasing filter.
    divisor = np.gcd(PHONE_RATE, rate)
    audio = resample_poly(audio, PHONE_RATE // divisor, rate // divisor)

    # A 4th-order Butterworth band-pass filter. "sos" form is numerically stable;
    # sosfiltfilt filters forwards then backwards, so the speech isn't shifted in time.
    sos = butter(4, [300, 3400], btype="bandpass", fs=PHONE_RATE, output="sos")
    audio = sosfiltfilt(sos, audio)

    # Noise level from the target signal-to-noise ratio. A fixed seed per clip
    # means re-running gives exactly the same file.
    rng = np.random.default_rng(seed)
    signal_power = np.mean(audio**2) + 1e-12
    noise_power = signal_power / (10 ** (NOISE_SNR_DB / 10))
    audio = audio + rng.normal(0, np.sqrt(noise_power), size=audio.shape)

    # Keep samples inside [-1, 1] so the WAV doesn't clip (crackle).
    peak = np.max(np.abs(audio))
    if peak > 0.99:
        audio = audio * (0.99 / peak)
    return audio.astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate test-set audio with OpenAI TTS.")
    parser.add_argument("--limit", type=int, default=None, help="only process the first N sentences")
    args = parser.parse_args()

    sentences = load_testset(splits=None)  # every split, incl. test-2 (appended last, so old voices don't move)
    selected = sentences[: args.limit] if args.limit else sentences

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    PHONE_DIR.mkdir(parents=True, exist_ok=True)

    # Cost check BEFORE spending anything: the full set, and what this run will actually generate.
    todo = [s for s in selected if not (CLEAN_DIR / f"{s.id}.wav").exists()]
    print(f"Estimated cost for the FULL set ({len(sentences)} clips): ~${estimate_cost([s.text for s in sentences]):.3f}")
    print(f"This run: {len(selected)} clips selected, {len(todo)} to generate "
          f"(~${estimate_cost([s.text for s in todo]):.3f}), {len(selected) - len(todo)} already exist.\n")

    # Only create the OpenAI client if we actually need to call the API.
    tts = None
    if todo:
        if settings.openai_api_key is None:
            print("[ERROR] OPENAI_API_KEY is not set. Add it to .env (see .env.example).")
            return 1
        tts = TTS()

    manifest = []
    for index, s in enumerate(sentences):
        voice, speed = voice_and_speed(index)
        clean_path = CLEAN_DIR / f"{s.id}.wav"
        phone_path = PHONE_DIR / f"{s.id}.wav"
        within_limit = args.limit is None or index < args.limit

        # --limit only caps how many NEW clips we generate. The manifest always lists every
        # clip already on disk, so a small test run never shrinks the manifest.
        if not clean_path.exists() and not within_limit:
            continue

        # Step 1: clean clip from TTS (skipped if it already exists, so re-runs are free).
        if not clean_path.exists():
            try:
                wav_bytes = tts.speak(s.text, voice, speed)
            except openai.OpenAIError as err:
                print(f"[ERROR] {s.id}: {type(err).__name__}: {err}")
                return 1
            clean_path.write_bytes(wav_bytes)
            print(f"  {s.id}  {voice:<8} x{speed:<4}  {s.text[:60]}")

        # Step 2: phone-quality copy (pure local maths, costs nothing).
        audio, rate = sf.read(io.BytesIO(clean_path.read_bytes()), dtype="float32")
        if not phone_path.exists():
            seed = int(s.id[1:])  # "s042" -> 42
            sf.write(phone_path, make_phone_quality(audio, rate, seed), PHONE_RATE, subtype="PCM_16")

        manifest.append({
            "id": s.id, "split": s.split, "category": s.category, "direction": s.direction, "text": s.text,
            "voice": voice, "speed": speed,
            # Paths relative to the project root with forward slashes, so they work on Windows and Linux (EC2).
            "clean_path": clean_path.relative_to(PROJECT_ROOT).as_posix(),
            "phone_path": phone_path.relative_to(PROJECT_ROOT).as_posix(),
            "duration_seconds": round(len(audio) / rate, 2),
        })

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    total_minutes = sum(m["duration_seconds"] for m in manifest) / 60
    spent = 0.0
    if tts is not None and tts.chars:
        # The real bill depends on the model used; estimate it the same way as above.
        new_minutes = sum(m["duration_seconds"] for m in manifest if m["id"] in {s.id for s in todo}) / 60
        spent = new_minutes * PRICE_PER_MINUTE_MINI_TTS if tts.model == settings.tts_model else tts.chars * PRICE_PER_CHAR_TTS1
        print(f"\nModel used: {tts.model}")
    print(f"\n[OK] {len(manifest)} clips in manifest, {total_minutes:.1f} minutes of audio.")
    print(f"Estimated cost of this run: ~${spent:.3f}")
    print(f"Manifest: {MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
