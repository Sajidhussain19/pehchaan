# data/results — Results

Transcripts and evaluation reports. Written by **Modules 4-5**.

- `baseline_{variant}_{audio}_{model}.json`: Module 4 transcripts.
  - `variant`: `plain` (baseline a) or `hints` (baseline b, KB names in the prompt)
  - `audio`: `clean`, `phone` or `real`
  - `meta` holds the variant, audio, model and hint-prompt size (included / excluded entities)
  - `clips` maps each clip id to: reference_text, transcript, latency_ms, cost_estimate_usd, split
  - Re-running `scripts/run_baseline.py` skips clips that are already here (free).
