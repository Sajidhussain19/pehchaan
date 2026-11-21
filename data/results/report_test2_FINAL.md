# Pehchaan evaluation: test2 split, audio = all

Generated 2026-11-21T19:05:44. Systems: (a) plain STT, (c) LLM baseline, Pehchaan v1, Pehchaan v2.

Every number is shown with raw counts. A clarify decision takes no action until the user answers.

### Overall: transcript metrics

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 36/52 = 69% | 47/52 = 90% | 45/52 = 87% | 49/52 = 94% |
| wer | 349/956 = 37% | 237/956 = 25% | 204/956 = 21% | 196/956 = 21% |
| over_correction_rate | 0/36 = 0% | 3/36 = 8% | 5/36 = 14% | 2/36 = 6% |

### Overall: decision metrics (systems that make decisions)

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| behaviour_accuracy | - | 69/90 = 77% | 78/90 = 87% | 82/90 = 91% |
| exact_action_target_accuracy | - | 34/40 = 85% | 29/40 = 72% | 36/40 = 90% |
| time_accuracy | - | 16/16 = 100% | 15/16 = 94% | 16/16 = 100% |
| wrong_target_rate | - | 10/90 = 11% | 9/90 = 10% | 2/90 = 2% |
| unnecessary_question_rate | - | 0/78 = 0% | 5/78 = 6% | 4/78 = 5% |
| missed_clarification_rate | - | 8/8 = 100% | 2/8 = 25% | 2/8 = 25% |
| clarify_candidates_ok | - | 0/0 = n/a | 6/6 = 100% | 6/6 = 100% |
| reference_resolution_accuracy | - | 10/14 = 71% | 11/14 = 79% | 11/14 = 79% |
| no_llm_rate | - | 0/90 = 0% | 83/90 = 92% | 84/90 = 93% |
| latency_ms_mean | - | 1727.5 | 249.7 | 187.5 |
| latency_ms_median | - | 1669.8 | 12.7 | 10.8 |
| cost_usd_mean | - | 0.000998 | 7e-06 | 7e-06 |

### Audio = clean

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 17/26 = 65% | 24/26 = 92% | 22/26 = 85% | 24/26 = 92% |
| wer | 173/478 = 36% | 119/478 = 25% | 103/478 = 22% | 99/478 = 21% |
| over_correction_rate | 0/18 = 0% | 1/18 = 6% | 2/18 = 11% | 1/18 = 6% |
| behaviour_accuracy | - | 35/45 = 78% | 39/45 = 87% | 41/45 = 91% |
| exact_action_target_accuracy | - | 17/20 = 85% | 14/20 = 70% | 18/20 = 90% |
| time_accuracy | - | 8/8 = 100% | 7/8 = 88% | 8/8 = 100% |
| wrong_target_rate | - | 5/45 = 11% | 4/45 = 9% | 1/45 = 2% |
| unnecessary_question_rate | - | 0/39 = 0% | 3/39 = 8% | 2/39 = 5% |
| missed_clarification_rate | - | 4/4 = 100% | 1/4 = 25% | 1/4 = 25% |
| clarify_candidates_ok | - | 0/0 = n/a | 3/3 = 100% | 3/3 = 100% |
| reference_resolution_accuracy | - | 5/7 = 71% | 5/7 = 71% | 5/7 = 71% |

### Audio = phone

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 19/26 = 73% | 23/26 = 88% | 23/26 = 88% | 25/26 = 96% |
| wer | 176/478 = 37% | 118/478 = 25% | 101/478 = 21% | 97/478 = 20% |
| over_correction_rate | 0/18 = 0% | 2/18 = 11% | 3/18 = 17% | 1/18 = 6% |
| behaviour_accuracy | - | 34/45 = 76% | 39/45 = 87% | 41/45 = 91% |
| exact_action_target_accuracy | - | 17/20 = 85% | 15/20 = 75% | 18/20 = 90% |
| time_accuracy | - | 8/8 = 100% | 8/8 = 100% | 8/8 = 100% |
| wrong_target_rate | - | 5/45 = 11% | 5/45 = 11% | 1/45 = 2% |
| unnecessary_question_rate | - | 0/39 = 0% | 2/39 = 5% | 2/39 = 5% |
| missed_clarification_rate | - | 4/4 = 100% | 1/4 = 25% | 1/4 = 25% |
| clarify_candidates_ok | - | 0/0 = n/a | 3/3 = 100% | 3/3 = 100% |
| reference_resolution_accuracy | - | 5/7 = 71% | 6/7 = 86% | 6/7 = 86% |

### Category = ambiguous

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 4/4 = 100% | 4/4 = 100% | 4/4 = 100% | 4/4 = 100% |
| wer | 4/60 = 7% | 4/60 = 7% | 4/60 = 7% | 4/60 = 7% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | 2/8 = 25% | 6/8 = 75% | 6/8 = 75% |
| exact_action_target_accuracy | - | 4/4 = 100% | 2/4 = 50% | 2/4 = 50% |
| time_accuracy | - | 2/2 = 100% | 2/2 = 100% | 2/2 = 100% |
| wrong_target_rate | - | 4/8 = 50% | 0/8 = 0% | 0/8 = 0% |
| unnecessary_question_rate | - | 0/4 = 0% | 2/4 = 50% | 2/4 = 50% |
| missed_clarification_rate | - | 4/4 = 100% | 0/4 = 0% | 0/4 = 0% |
| clarify_candidates_ok | - | 0/0 = n/a | 4/4 = 100% | 4/4 = 100% |
| reference_resolution_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = context_mismatch

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 2/38 = 5% | 2/38 = 5% | 2/38 = 5% | 2/38 = 5% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | 2/4 = 50% | 4/4 = 100% | 4/4 = 100% |
| exact_action_target_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | 0/4 = 0% | 0/4 = 0% | 0/4 = 0% |
| unnecessary_question_rate | - | 0/2 = 0% | 0/2 = 0% | 0/2 = 0% |
| missed_clarification_rate | - | 2/2 = 100% | 0/2 = 0% | 0/2 = 0% |
| clarify_candidates_ok | - | 0/0 = n/a | 2/2 = 100% | 2/2 = 100% |
| reference_resolution_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = control

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 220/110 = 200% | 119/110 = 108% | 125/110 = 114% | 123/110 = 112% |
| over_correction_rate | 0/16 = 0% | 0/16 = 0% | 2/16 = 12% | 0/16 = 0% |
| behaviour_accuracy | - | 16/16 = 100% | 14/16 = 88% | 16/16 = 100% |
| exact_action_target_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | 0/16 = 0% | 0/16 = 0% | 0/16 = 0% |
| unnecessary_question_rate | - | 0/16 = 0% | 0/16 = 0% | 0/16 = 0% |
| missed_clarification_rate | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = in_kb

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 32/48 = 67% | 43/48 = 90% | 41/48 = 85% | 45/48 = 94% |
| wer | 32/380 = 8% | 19/380 = 5% | 22/380 = 6% | 17/380 = 4% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | 19/28 = 68% | 26/28 = 93% | 27/28 = 96% |
| exact_action_target_accuracy | - | 20/24 = 83% | 16/24 = 67% | 23/24 = 96% |
| time_accuracy | - | 8/8 = 100% | 7/8 = 88% | 8/8 = 100% |
| wrong_target_rate | - | 0/28 = 0% | 6/28 = 21% | 0/28 = 0% |
| unnecessary_question_rate | - | 0/28 = 0% | 2/28 = 7% | 1/28 = 4% |
| missed_clarification_rate | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = out_of_kb

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 77/194 = 40% | 72/194 = 37% | 37/194 = 19% | 36/194 = 19% |
| over_correction_rate | 0/16 = 0% | 1/16 = 6% | 3/16 = 19% | 2/16 = 12% |
| behaviour_accuracy | - | 16/16 = 100% | 13/16 = 81% | 14/16 = 88% |
| exact_action_target_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | 2/2 = 100% | 2/2 = 100% | 2/2 = 100% |
| wrong_target_rate | - | 0/16 = 0% | 3/16 = 19% | 2/16 = 12% |
| unnecessary_question_rate | - | 0/16 = 0% | 0/16 = 0% | 0/16 = 0% |
| missed_clarification_rate | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = reference

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 12/104 = 12% | 13/104 = 12% | 12/104 = 12% | 12/104 = 12% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | 8/10 = 80% | 7/10 = 70% | 7/10 = 70% |
| exact_action_target_accuracy | - | 8/8 = 100% | 7/8 = 88% | 7/8 = 88% |
| time_accuracy | - | 4/4 = 100% | 4/4 = 100% | 4/4 = 100% |
| wrong_target_rate | - | 2/10 = 20% | 0/10 = 0% | 0/10 = 0% |
| unnecessary_question_rate | - | 0/8 = 0% | 1/8 = 12% | 1/8 = 12% |
| missed_clarification_rate | - | 2/2 = 100% | 2/2 = 100% | 2/2 = 100% |
| clarify_candidates_ok | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | 8/10 = 80% | 7/10 = 70% | 7/10 = 70% |

### Category = stale_default

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 0/38 = 0% | 4/38 = 11% | 0/38 = 0% | 0/38 = 0% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | 4/4 = 100% | 4/4 = 100% | 4/4 = 100% |
| exact_action_target_accuracy | - | 2/4 = 50% | 4/4 = 100% | 4/4 = 100% |
| time_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | 2/4 = 50% | 0/4 = 0% | 0/4 = 0% |
| unnecessary_question_rate | - | 0/4 = 0% | 0/4 = 0% | 0/4 = 0% |
| missed_clarification_rate | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | 2/4 = 50% | 4/4 = 100% | 4/4 = 100% |

### Category = unfamiliar_near_match

| metric | (a) plain STT | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 2/32 = 6% | 4/32 = 12% | 2/32 = 6% | 2/32 = 6% |
| over_correction_rate | 0/4 = 0% | 2/4 = 50% | 0/4 = 0% | 0/4 = 0% |
| behaviour_accuracy | - | 2/4 = 50% | 4/4 = 100% | 4/4 = 100% |
| exact_action_target_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | 2/4 = 50% | 0/4 = 0% | 0/4 = 0% |
| unnecessary_question_rate | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| missed_clarification_rate | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

## Clip by clip: Pehchaan v2 vs (c) LLM baseline

**Pehchaan v2 wins 25, ties 62, loses 3** (of 90 clips; win = Pehchaan v2 did better).

| clip | audio | category | result | v2 outcome | c outcome | said |
|---|---|---|---|---|---|---|
| s174 | clean | in_kb | win | ok | wrong_action | Remind me to pick up the BP tablets from Manjunatha Medicals |
| s176 | clean | in_kb | win | ok | entity_miss | Ask Sree Durga Bhavani Medicals in LB Nagar to keep the insu |
| s185 | clean | out_of_kb | loss | wrong_target | ok | Tell Dheeraj to bring the projector to the Shadnagar office. |
| s186 | clean | in_kb | win | ok | wrong_behaviour | Call Thirumalai Selvan and ask when he will pay the rent. |
| s187 | clean | in_kb | win | ok | wrong_behaviour | Remind me to meet Unnikrishnan Nair at Kochi airport on Mond |
| s191 | clean | in_kb | win | ok | wrong_behaviour | How long does it take from Hitech City to Golconda Fort in t |
| s192 | clean | in_kb | win | ok | wrong_behaviour | Call Smruti Rekha Behera and ask about the night shift on We |
| s194 | clean | reference | loss | unnecessary_question | ok | Tell Pinni I will visit her on Sunday evening. |
| s198 | clean | reference | win | missed_clarification | wrong_target | Ask my neighbour to collect the courier while I'm away. |
| s199 | clean | ambiguous | win | ok | wrong_target | Text Ravi that I'll be late for dinner. |
| s202 | clean | ambiguous | win | ok | wrong_target | Call Lakshmi tomorrow morning. |
| s203 | clean | context_mismatch | win | ok | missed_clarification | Book a table at Arif Biryani Point tonight. |
| s206 | clean | unfamiliar_near_match | win | ok | wrong_target | Tell Anjana the cake order is confirmed. |
| s208 | clean | stale_default | win | ok | wrong_target | Call my doctor to fix an appointment for my son's braces. |
| s176 | phone | in_kb | win | ok | entity_miss | Ask Sree Durga Bhavani Medicals in LB Nagar to keep the insu |
| s183 | phone | out_of_kb | loss | wrong_target | ok | Message Farhan that the cricket nets are booked at Kokapet. |
| s185 | phone | out_of_kb | win | ok | over_corrected | Tell Dheeraj to bring the projector to the Shadnagar office. |
| s186 | phone | in_kb | win | ok | wrong_behaviour | Call Thirumalai Selvan and ask when he will pay the rent. |
| s187 | phone | in_kb | win | ok | wrong_behaviour | Remind me to meet Unnikrishnan Nair at Kochi airport on Mond |
| s188 | phone | in_kb | win | ok | entity_miss | Message Subhashis Chattopadhyay that the thesis draft is rea |
| s191 | phone | in_kb | win | ok | wrong_behaviour | How long does it take from Hitech City to Golconda Fort in t |
| s192 | phone | in_kb | win | ok | wrong_behaviour | Call Smruti Rekha Behera and ask about the night shift on We |
| s198 | phone | reference | win | missed_clarification | wrong_target | Ask my neighbour to collect the courier while I'm away. |
| s199 | phone | ambiguous | win | ok | wrong_target | Text Ravi that I'll be late for dinner. |
| s202 | phone | ambiguous | win | ok | wrong_target | Call Lakshmi tomorrow morning. |
| s203 | phone | context_mismatch | win | ok | missed_clarification | Book a table at Arif Biryani Point tonight. |
| s206 | phone | unfamiliar_near_match | win | ok | wrong_target | Tell Anjana the cake order is confirmed. |
| s208 | phone | stale_default | win | ok | wrong_target | Call my doctor to fix an appointment for my son's braces. |
