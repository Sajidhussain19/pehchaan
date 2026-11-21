"""
scripts/fetch_real_speech.py — downloads a small sample of REAL Indian-accented English speech.

WHAT: Fetches ~40 short clips, each from a DIFFERENT speaker, from AI4Bharat's "Svarah" dataset
      (CC BY 4.0) using the Hugging Face dataset-viewer API. It saves:
        data/realspeech/audio/r001.wav ...   the clips
        data/realspeech/manifest.json        id, split, reference transcript, speaker id, duration, source row
        data/realspeech/ATTRIBUTION.md       licence + citation (CC BY requires attribution)
      It stops before the sample would exceed 50 MB.
WHY:  Our main test set is synthetic (text-to-speech). Real people hesitate and have strong regional
      accents. These clips mostly contain none of our KB names, so they answer the key safety
      question: does Pehchaan make a real transcript WORSE (over-correction)?

BEFORE RUNNING (one-time, done by you, not by the script):
  1. Log in to Hugging Face and accept the dataset conditions at
     https://huggingface.co/datasets/ai4bharat/Svarah  (it is "gated": you share your HF username/email
     with AI4Bharat to get access).
  2. Create a read token at https://huggingface.co/settings/tokens and add HF_TOKEN=... to your .env.

Run from the project root:
    python scripts/fetch_real_speech.py            # 40 clips
    python scripts/fetch_real_speech.py --count 10
"""

import argparse
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
import soundfile as sf

# Make the project root importable when this file runs as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import PROJECT_ROOT, settings  # noqa: E402

DATASET = "ai4bharat/Svarah"
API = "https://datasets-server.huggingface.co"
OUT_DIR = PROJECT_ROOT / "data" / "realspeech"
AUDIO_DIR = OUT_DIR / "audio"
MAX_TOTAL_BYTES = 50 * 1024 * 1024  # stay under 50 MB so the sample can live in git
MAX_CLIP_SECONDS = 15.0  # short clips keep transcription cheap and the sample varied
PAGE_SIZE = 100  # the dataset-viewer API returns at most 100 rows per request

# Column names differ between datasets, so we accept a few common spellings.
TEXT_COLUMNS = ("text", "transcript", "transcription", "sentence")
SPEAKER_COLUMNS = ("speaker_id", "speaker", "spk_id", "client_id")
DURATION_COLUMNS = ("duration", "audio_duration")

ATTRIBUTION = """# Real-speech sample: attribution

Clips in this folder come from **Svarah** by AI4Bharat (IIT Madras):
https://huggingface.co/datasets/ai4bharat/Svarah

**Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0),
https://creativecommons.org/licenses/by/4.0/
We use a small unmodified sample of clips with their reference transcripts, for evaluation only.

**Citation:**
Tahir Javed et al., "Svarah: Evaluating English ASR Systems on Indian Accents", INTERSPEECH 2023
(arXiv:2305.15760).
"""


def get_json(client: httpx.Client, path: str, **params) -> dict:
    """Call the dataset-viewer API and explain the usual errors in plain words."""
    response = client.get(f"{API}/{path}", params={"dataset": DATASET, **params})
    if response.status_code in (401, 403):
        raise SystemExit(
            "[ERROR] Hugging Face refused access (HTTP %d). Make sure you accepted the dataset conditions at\n"
            "        https://huggingface.co/datasets/%s and that HF_TOKEN in .env is a valid read token."
            % (response.status_code, DATASET)
        )
    response.raise_for_status()
    return response.json()


def pick_column(row: dict, candidates: tuple[str, ...]) -> str | None:
    """Return the first column name from `candidates` that exists in this row."""
    return next((c for c in candidates if c in row), None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download a small real-speech sample (Svarah, CC BY 4.0).")
    parser.add_argument("--count", type=int, default=40, help="number of clips (one per speaker)")
    args = parser.parse_args()

    if settings.hf_token is None:
        print("[ERROR] HF_TOKEN is not set. Accept the conditions at "
              f"https://huggingface.co/datasets/{DATASET} and add HF_TOKEN=... to .env (see .env.example).")
        return 1

    headers = {"Authorization": f"Bearer {settings.hf_token.get_secret_value()}"}
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(headers=headers, timeout=60, follow_redirects=True) as client:
        # Step 1: find which config/split exists (Svarah publishes a "test" split).
        splits = get_json(client, "splits")["splits"]
        config, split = splits[0]["config"], splits[0]["split"]
        print(f"Using {DATASET} config={config!r} split={split!r}")

        clips, speakers_seen, total_bytes, offset = [], set(), 0, 0
        while len(clips) < args.count:
            # Step 2: read the next page of rows (metadata + signed audio URLs, not the whole dataset).
            page = get_json(client, "rows", config=config, split=split, offset=offset, length=PAGE_SIZE)
            rows = page.get("rows", [])
            if not rows:
                break
            audio_col = next(f["name"] for f in page["features"] if f["type"].get("_type") == "Audio")

            for item in rows:
                row = item["row"]
                text_col = pick_column(row, TEXT_COLUMNS)
                speaker_col = pick_column(row, SPEAKER_COLUMNS)
                if text_col is None or speaker_col is None or not row.get(audio_col):
                    continue
                speaker = str(row[speaker_col])
                # One clip per speaker: 40 voices tell us more than 40 clips of one voice.
                if speaker in speakers_seen:
                    continue
                duration_col = pick_column(row, DURATION_COLUMNS)
                if duration_col and float(row[duration_col]) > MAX_CLIP_SECONDS:
                    continue

                # Step 3: download this one clip. The signed URL is on a Hugging Face host;
                # we only send our token to Hugging Face hosts.
                src = row[audio_col][0]["src"]
                host = urlparse(src).hostname or ""
                audio_headers = headers if host.endswith("huggingface.co") else {}
                audio_bytes = httpx.get(src, headers=audio_headers, timeout=60, follow_redirects=True).content
                if total_bytes + len(audio_bytes) > MAX_TOTAL_BYTES:
                    print("Reached the 50 MB size cap, stopping.")
                    break

                # Measure the real duration from the audio itself.
                try:
                    info = sf.info(io.BytesIO(audio_bytes))
                    duration = info.frames / info.samplerate
                except Exception:  # noqa: BLE001 (format soundfile can't read: fall back to metadata)
                    duration = float(row[duration_col]) if duration_col else 0.0
                if duration <= 0 or duration > MAX_CLIP_SECONDS:
                    continue

                clip_id = f"r{len(clips) + 1:03d}"
                ext = ".wav" if "wav" in row[audio_col][0].get("type", "wav") else Path(urlparse(src).path).suffix
                audio_path = AUDIO_DIR / f"{clip_id}{ext}"
                audio_path.write_bytes(audio_bytes)
                total_bytes += len(audio_bytes)
                speakers_seen.add(speaker)
                clips.append({
                    "id": clip_id,
                    # Every 3rd clip goes to dev, the rest are held out for final numbers.
                    "split": "dev" if len(clips) % 3 == 0 else "test",
                    "category": "real_speech",
                    "text": str(row[text_col]).strip(),
                    "speaker_id": speaker,
                    "audio_path": audio_path.relative_to(PROJECT_ROOT).as_posix(),
                    "duration_seconds": round(duration, 2),
                    "expected_behaviour": "keep",
                    "source": DATASET,
                    "source_id": f"{config}/{split}/{item['row_idx']}",
                })
                print(f"  {clip_id}  speaker {speaker:<12} {duration:5.1f}s  {str(row[text_col])[:60]}")
                if len(clips) >= args.count:
                    break
            else:
                offset += PAGE_SIZE
                continue
            break  # inner loop hit the size cap or the target count

    (OUT_DIR / "manifest.json").write_text(json.dumps(clips, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "ATTRIBUTION.md").write_text(ATTRIBUTION, encoding="utf-8")
    minutes = sum(c["duration_seconds"] for c in clips) / 60
    print(f"\n[OK] {len(clips)} clips from {len(speakers_seen)} speakers, {minutes:.1f} min, "
          f"{total_bytes / 1e6:.1f} MB -> data/realspeech/")
    print("Next: python -m app.testset.validate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
