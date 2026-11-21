# data/results — Results

Transcripts, decisions and evaluation reports. Written by **Modules 4, 5 and 8**.

- `pehchaan_{audio}_{version}.json`: Module 8 Pehchaan decisions (same `Decision` format as baseline (c)).
- `pehchaan_llm_cache.json`: cached answers of Pehchaan's small LLM fallback (key = model + instructions + prompt).

- `llm_baseline_{audio}_{model}.json`: Module 5 baseline (c) decisions, one `Decision` per clip id (cached).
- `report_{split}_{audio}.md/.json`: Module 5 evaluation reports (`scripts/evaluate.py`).
- `test_runs.log`: every time the held-out test split was scored (created only by `--final`).
- `baseline_{variant}_{audio}_{model}.json`: Module 4 transcripts.
  - `variant`: `plain` (baseline a) or `hints` (baseline b, KB names in the prompt)
  - `audio`: `clean`, `phone` or `real`
  - `meta` holds the variant, audio, model and hint-prompt size (included / excluded entities)
  - `clips` maps each clip id to: reference_text, transcript, latency_ms, cost_estimate_usd, split
  - Re-running `scripts/run_baseline.py` skips clips that are already here (free).
