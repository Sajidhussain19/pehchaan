# Pehchaan evaluation: dev split, audio = all

Generated 2026-11-21T14:50:28. Systems: (a) plain STT, (b) STT + hints, (c) LLM baseline. Not available yet: Pehchaan.

Every number is shown with raw counts. A clarify decision takes no action until the user answers.

### Overall: transcript metrics

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 41/64 = 64% | 49/64 = 77% | 55/64 = 86% |
| wer | 277/1163 = 24% | 248/1163 = 21% | 198/1163 = 17% |
| over_correction_rate | 0/34 = 0% | 0/34 = 0% | 1/34 = 3% |

### Overall: decision metrics (systems that make decisions)

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| behaviour_accuracy | - | - | 85/104 = 82% |
| exact_action_target_accuracy | - | - | 40/52 = 77% |
| time_accuracy | - | - | 15/16 = 94% |
| wrong_target_rate | - | - | 9/104 = 9% |
| unnecessary_question_rate | - | - | 2/92 = 2% |
| missed_clarification_rate | - | - | 7/8 = 88% |
| clarify_candidates_ok | - | - | 1/1 = 100% |
| reference_resolution_accuracy | - | - | 8/14 = 57% |
| no_llm_rate | - | - | 0/104 = 0% |
| latency_ms_mean | - | - | 1542.4 |
| latency_ms_median | - | - | 1495.3 |
| cost_usd_mean | - | - | 0.000972 |

### Audio = clean

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 22/32 = 69% | 24/32 = 75% | 29/32 = 91% |
| wer | 123/466 = 26% | 117/466 = 25% | 90/466 = 19% |
| over_correction_rate | 0/10 = 0% | 0/10 = 0% | 0/10 = 0% |
| behaviour_accuracy | - | - | 37/45 = 82% |
| exact_action_target_accuracy | - | - | 21/26 = 81% |
| time_accuracy | - | - | 7/8 = 88% |
| wrong_target_rate | - | - | 3/45 = 7% |
| unnecessary_question_rate | - | - | 1/39 = 3% |
| missed_clarification_rate | - | - | 3/4 = 75% |
| clarify_candidates_ok | - | - | 1/1 = 100% |
| reference_resolution_accuracy | - | - | 4/7 = 57% |

### Audio = phone

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 19/32 = 59% | 25/32 = 78% | 26/32 = 81% |
| wer | 129/466 = 28% | 114/466 = 24% | 83/466 = 18% |
| over_correction_rate | 0/10 = 0% | 0/10 = 0% | 1/10 = 10% |
| behaviour_accuracy | - | - | 34/45 = 76% |
| exact_action_target_accuracy | - | - | 19/26 = 73% |
| time_accuracy | - | - | 8/8 = 100% |
| wrong_target_rate | - | - | 6/45 = 13% |
| unnecessary_question_rate | - | - | 1/39 = 3% |
| missed_clarification_rate | - | - | 4/4 = 100% |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 4/7 = 57% |

### Audio = real

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 25/231 = 11% | 17/231 = 7% | 25/231 = 11% |
| over_correction_rate | 0/14 = 0% | 0/14 = 0% | 0/14 = 0% |
| behaviour_accuracy | - | - | 14/14 = 100% |
| exact_action_target_accuracy | - | - | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a |
| wrong_target_rate | - | - | 0/14 = 0% |
| unnecessary_question_rate | - | - | 0/14 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a |

### Category = ambiguous

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 2/4 = 50% | 2/4 = 50% | 2/4 = 50% |
| wer | 3/68 = 4% | 2/68 = 3% | 3/68 = 4% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 1/8 = 12% |
| exact_action_target_accuracy | - | - | 2/4 = 50% |
| time_accuracy | - | - | 0/0 = n/a |
| wrong_target_rate | - | - | 3/8 = 38% |
| unnecessary_question_rate | - | - | 1/4 = 25% |
| missed_clarification_rate | - | - | 3/4 = 75% |
| clarify_candidates_ok | - | - | 1/1 = 100% |
| reference_resolution_accuracy | - | - | 0/0 = n/a |

### Category = context_mismatch

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 8/70 = 11% | 8/70 = 11% | 8/70 = 11% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 4/6 = 67% |
| exact_action_target_accuracy | - | - | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a |
| wrong_target_rate | - | - | 2/6 = 33% |
| unnecessary_question_rate | - | - | 0/4 = 0% |
| missed_clarification_rate | - | - | 2/2 = 100% |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a |

### Category = control

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 4/76 = 5% | 4/76 = 5% | 4/76 = 5% |
| over_correction_rate | 0/8 = 0% | 0/8 = 0% | 0/8 = 0% |
| behaviour_accuracy | - | - | 6/8 = 75% |
| exact_action_target_accuracy | - | - | 0/0 = n/a |
| time_accuracy | - | - | 2/2 = 100% |
| wrong_target_rate | - | - | 0/8 = 0% |
| unnecessary_question_rate | - | - | 0/8 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a |

### Category = in_kb

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 39/60 = 65% | 47/60 = 78% | 53/60 = 88% |
| wer | 146/490 = 30% | 132/490 = 27% | 104/490 = 21% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 36/42 = 86% |
| exact_action_target_accuracy | - | - | 30/36 = 83% |
| time_accuracy | - | - | 11/12 = 92% |
| wrong_target_rate | - | - | 1/42 = 2% |
| unnecessary_question_rate | - | - | 1/42 = 2% |
| missed_clarification_rate | - | - | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a |

### Category = out_of_kb

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 35/72 = 49% | 32/72 = 44% | 35/72 = 49% |
| over_correction_rate | 0/8 = 0% | 0/8 = 0% | 1/8 = 12% |
| behaviour_accuracy | - | - | 8/8 = 100% |
| exact_action_target_accuracy | - | - | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a |
| wrong_target_rate | - | - | 0/8 = 0% |
| unnecessary_question_rate | - | - | 0/8 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a |

### Category = real_speech

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 25/231 = 11% | 17/231 = 7% | 25/231 = 11% |
| over_correction_rate | 0/14 = 0% | 0/14 = 0% | 0/14 = 0% |
| behaviour_accuracy | - | - | 14/14 = 100% |
| exact_action_target_accuracy | - | - | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a |
| wrong_target_rate | - | - | 0/14 = 0% |
| unnecessary_question_rate | - | - | 0/14 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a |

### Category = reference

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 56/102 = 55% | 53/102 = 52% | 17/102 = 17% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 10/12 = 83% |
| exact_action_target_accuracy | - | - | 6/10 = 60% |
| time_accuracy | - | - | 2/2 = 100% |
| wrong_target_rate | - | - | 3/12 = 25% |
| unnecessary_question_rate | - | - | 0/10 = 0% |
| missed_clarification_rate | - | - | 2/2 = 100% |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 6/12 = 50% |

### Category = stale_default

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 0/14 = 0% | 0/14 = 0% | 2/14 = 14% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 2/2 = 100% |
| exact_action_target_accuracy | - | - | 2/2 = 100% |
| time_accuracy | - | - | 0/0 = n/a |
| wrong_target_rate | - | - | 0/2 = 0% |
| unnecessary_question_rate | - | - | 0/2 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 2/2 = 100% |

### Category = unfamiliar_near_match

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 0/40 = 0% | 0/40 = 0% | 0/40 = 0% |
| over_correction_rate | 0/4 = 0% | 0/4 = 0% | 0/4 = 0% |
| behaviour_accuracy | - | - | 4/4 = 100% |
| exact_action_target_accuracy | - | - | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a |
| wrong_target_rate | - | - | 0/4 = 0% |
| unnecessary_question_rate | - | - | 0/0 = n/a |
| missed_clarification_rate | - | - | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a |

## Clip by clip: (c) LLM baseline vs (b) STT + hints

**(c) LLM baseline wins 8, ties 92, loses 4** (of 104 clips; win = (c) LLM baseline did better).

| clip | audio | category | result | c outcome | b outcome | said |
|---|---|---|---|---|---|---|
| s007 | clean | in_kb | loss | entity_miss | ok | Call Srinivasan Iyer and wish him a happy birthday. |
| s030 | clean | in_kb | win | ok | entity_miss | Saar, Chikkanna here, the balcony plants need new pots. |
| s033 | clean | in_kb | win | ok | entity_miss | Call Sreekumar Menon and tell him I land in Thiruvananthapur |
| s036 | clean | in_kb | win | ok | entity_miss | Sharma Ji bol raha hoon, society meeting kal shaam saat baje |
| s046 | clean | in_kb | win | ok | entity_miss | Call Harjeet Kaur aunty and wish her for Lohri. |
| s049 | clean | in_kb | win | ok | entity_miss | Jignesh Shah ne bola stationery kal tak ready ho jayegi. |
| s020 | phone | in_kb | loss | entity_miss | ok | Call Vijayalakshmi aunty and ask for the Dilsukhnagar addres |
| s030 | phone | in_kb | win | ok | entity_miss | Saar, Chikkanna here, the balcony plants need new pots. |
| s033 | phone | in_kb | loss | entity_miss | ok | Call Sreekumar Menon and tell him I land in Thiruvananthapur |
| s036 | phone | in_kb | win | ok | entity_miss | Sharma Ji bol raha hoon, society meeting kal shaam saat baje |
| s039 | phone | in_kb | loss | entity_miss | ok | Book the Diwali sweets order at Agarwal Mithai Bhandar in Ko |
| s049 | phone | in_kb | win | ok | entity_miss | Jignesh Shah ne bola stationery kal tak ready ho jayegi. |
