# Pehchaan evaluation: dev split, audio = all

Generated 2026-11-21T16:22:11. Systems: (a) plain STT, (b) STT + hints, (c) LLM baseline, Pehchaan.

Every number is shown with raw counts. A clarify decision takes no action until the user answers.

### Overall: transcript metrics

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 58/98 = 59% | 79/98 = 81% | 81/98 = 83% | 96/98 = 98% |
| wer | 322/1575 = 20% | 271/1575 = 17% | 238/1575 = 15% | 147/1575 = 9% |
| over_correction_rate | 0/34 = 0% | 0/34 = 0% | 1/34 = 3% | 0/34 = 0% |

### Overall: decision metrics (systems that make decisions)

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| behaviour_accuracy | - | - | 106/146 = 73% | 138/146 = 95% |
| exact_action_target_accuracy | - | - | 63/86 = 73% | 84/86 = 98% |
| time_accuracy | - | - | 25/26 = 96% | 26/26 = 100% |
| wrong_target_rate | - | - | 20/146 = 14% | 0/146 = 0% |
| unnecessary_question_rate | - | - | 2/126 = 2% | 0/126 = 0% |
| missed_clarification_rate | - | - | 15/16 = 94% | 1/16 = 6% |
| clarify_candidates_ok | - | - | 1/1 = 100% | 13/15 = 87% |
| reference_resolution_accuracy | - | - | 12/24 = 50% | 23/24 = 96% |
| no_llm_rate | - | - | 0/146 = 0% | 132/146 = 90% |
| latency_ms_mean | - | - | 1613.2 | 135.8 |
| latency_ms_median | - | - | 1561.6 | 9.4 |
| cost_usd_mean | - | - | 0.000978 | 1e-05 |

### Audio = clean

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 32/49 = 65% | 39/49 = 80% | 43/49 = 88% | 49/49 = 100% |
| wer | 144/672 = 21% | 127/672 = 19% | 108/672 = 16% | 60/672 = 9% |
| over_correction_rate | 0/10 = 0% | 0/10 = 0% | 0/10 = 0% | 0/10 = 0% |
| behaviour_accuracy | - | - | 48/66 = 73% | 64/66 = 97% |
| exact_action_target_accuracy | - | - | 33/43 = 77% | 43/43 = 100% |
| time_accuracy | - | - | 12/13 = 92% | 13/13 = 100% |
| wrong_target_rate | - | - | 9/66 = 14% | 0/66 = 0% |
| unnecessary_question_rate | - | - | 1/56 = 2% | 0/56 = 0% |
| missed_clarification_rate | - | - | 7/8 = 88% | 0/8 = 0% |
| clarify_candidates_ok | - | - | 1/1 = 100% | 7/8 = 88% |
| reference_resolution_accuracy | - | - | 6/12 = 50% | 12/12 = 100% |

### Audio = phone

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 26/49 = 53% | 40/49 = 82% | 38/49 = 78% | 47/49 = 96% |
| wer | 153/672 = 23% | 127/672 = 19% | 105/672 = 16% | 62/672 = 9% |
| over_correction_rate | 0/10 = 0% | 0/10 = 0% | 1/10 = 10% | 0/10 = 0% |
| behaviour_accuracy | - | - | 44/66 = 67% | 60/66 = 91% |
| exact_action_target_accuracy | - | - | 30/43 = 70% | 41/43 = 95% |
| time_accuracy | - | - | 13/13 = 100% | 13/13 = 100% |
| wrong_target_rate | - | - | 11/66 = 17% | 0/66 = 0% |
| unnecessary_question_rate | - | - | 1/56 = 2% | 0/56 = 0% |
| missed_clarification_rate | - | - | 8/8 = 100% | 1/8 = 12% |
| clarify_candidates_ok | - | - | 0/0 = n/a | 6/7 = 86% |
| reference_resolution_accuracy | - | - | 6/12 = 50% | 11/12 = 92% |

### Audio = real

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 25/231 = 11% | 17/231 = 7% | 25/231 = 11% | 25/231 = 11% |
| over_correction_rate | 0/14 = 0% | 0/14 = 0% | 0/14 = 0% | 0/14 = 0% |
| behaviour_accuracy | - | - | 14/14 = 100% | 14/14 = 100% |
| exact_action_target_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | - | 0/14 = 0% | 0/14 = 0% |
| unnecessary_question_rate | - | - | 0/14 = 0% | 0/14 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |

### Category = ambiguous

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 3/8 = 38% | 4/8 = 50% | 5/8 = 62% | 7/8 = 88% |
| wer | 8/116 = 7% | 5/116 = 4% | 5/116 = 4% | 3/116 = 3% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 2/14 = 14% | 13/14 = 93% |
| exact_action_target_accuracy | - | - | 5/8 = 62% | 7/8 = 88% |
| time_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | - | 5/14 = 36% | 0/14 = 0% |
| unnecessary_question_rate | - | - | 1/8 = 12% | 0/8 = 0% |
| missed_clarification_rate | - | - | 5/6 = 83% | 0/6 = 0% |
| clarify_candidates_ok | - | - | 1/1 = 100% | 4/6 = 67% |
| reference_resolution_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |

### Category = context_mismatch

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 9/102 = 9% | 8/102 = 8% | 9/102 = 9% | 9/102 = 9% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 4/10 = 40% | 9/10 = 90% |
| exact_action_target_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | - | 3/10 = 30% | 0/10 = 0% |
| unnecessary_question_rate | - | - | 0/4 = 0% | 0/4 = 0% |
| missed_clarification_rate | - | - | 6/6 = 100% | 1/6 = 17% |
| clarify_candidates_ok | - | - | 0/0 = n/a | 5/5 = 100% |
| reference_resolution_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |

### Category = control

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 4/76 = 5% | 4/76 = 5% | 4/76 = 5% | 4/76 = 5% |
| over_correction_rate | 0/8 = 0% | 0/8 = 0% | 0/8 = 0% | 0/8 = 0% |
| behaviour_accuracy | - | - | 6/8 = 75% | 8/8 = 100% |
| exact_action_target_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | - | 2/2 = 100% | 2/2 = 100% |
| wrong_target_rate | - | - | 0/8 = 0% | 0/8 = 0% |
| unnecessary_question_rate | - | - | 0/8 = 0% | 0/8 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |

### Category = in_kb

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 53/88 = 60% | 73/88 = 83% | 74/88 = 84% | 87/88 = 99% |
| wer | 177/718 = 25% | 143/718 = 20% | 129/718 = 18% | 62/718 = 9% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 48/64 = 75% | 59/64 = 92% |
| exact_action_target_accuracy | - | - | 46/58 = 79% | 58/58 = 100% |
| time_accuracy | - | - | 19/20 = 95% | 20/20 = 100% |
| wrong_target_rate | - | - | 3/64 = 5% | 0/64 = 0% |
| unnecessary_question_rate | - | - | 1/64 = 2% | 0/64 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |

### Category = out_of_kb

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 35/72 = 49% | 32/72 = 44% | 35/72 = 49% | 15/72 = 21% |
| over_correction_rate | 0/8 = 0% | 0/8 = 0% | 1/8 = 12% | 0/8 = 0% |
| behaviour_accuracy | - | - | 8/8 = 100% | 8/8 = 100% |
| exact_action_target_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | - | 0/8 = 0% | 0/8 = 0% |
| unnecessary_question_rate | - | - | 0/8 = 0% | 0/8 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |

### Category = real_speech

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 25/231 = 11% | 17/231 = 7% | 25/231 = 11% | 25/231 = 11% |
| over_correction_rate | 0/14 = 0% | 0/14 = 0% | 0/14 = 0% | 0/14 = 0% |
| behaviour_accuracy | - | - | 14/14 = 100% | 14/14 = 100% |
| exact_action_target_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | - | 0/14 = 0% | 0/14 = 0% |
| unnecessary_question_rate | - | - | 0/14 = 0% | 0/14 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |

### Category = reference

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 62/162 = 38% | 58/162 = 36% | 25/162 = 15% | 27/162 = 17% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 14/18 = 78% | 17/18 = 94% |
| exact_action_target_accuracy | - | - | 10/14 = 71% | 13/14 = 93% |
| time_accuracy | - | - | 2/2 = 100% | 2/2 = 100% |
| wrong_target_rate | - | - | 5/18 = 28% | 0/18 = 0% |
| unnecessary_question_rate | - | - | 0/14 = 0% | 0/14 = 0% |
| missed_clarification_rate | - | - | 4/4 = 100% | 0/4 = 0% |
| clarify_candidates_ok | - | - | 0/0 = n/a | 4/4 = 100% |
| reference_resolution_accuracy | - | - | 10/18 = 56% | 17/18 = 94% |

### Category = stale_default

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 2/2 = 100% | 2/2 = 100% | 2/2 = 100% | 2/2 = 100% |
| wer | 2/58 = 3% | 4/58 = 7% | 6/58 = 10% | 2/58 = 3% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | - | - | 6/6 = 100% | 6/6 = 100% |
| exact_action_target_accuracy | - | - | 2/6 = 33% | 6/6 = 100% |
| time_accuracy | - | - | 2/2 = 100% | 2/2 = 100% |
| wrong_target_rate | - | - | 4/6 = 67% | 0/6 = 0% |
| unnecessary_question_rate | - | - | 0/6 = 0% | 0/6 = 0% |
| missed_clarification_rate | - | - | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 2/6 = 33% | 6/6 = 100% |

### Category = unfamiliar_near_match

| metric | (a) plain STT | (b) STT + hints | (c) LLM baseline | Pehchaan |
|---|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 0/40 = 0% | 0/40 = 0% | 0/40 = 0% | 0/40 = 0% |
| over_correction_rate | 0/4 = 0% | 0/4 = 0% | 0/4 = 0% | 0/4 = 0% |
| behaviour_accuracy | - | - | 4/4 = 100% | 4/4 = 100% |
| exact_action_target_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | - | - | 0/4 = 0% | 0/4 = 0% |
| unnecessary_question_rate | - | - | 0/0 = n/a | 0/0 = n/a |
| missed_clarification_rate | - | - | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | - | - | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | - | - | 0/0 = n/a | 0/0 = n/a |

## Clip by clip: (c) LLM baseline vs Pehchaan

**(c) LLM baseline wins 4, ties 88, loses 54** (of 146 clips; win = (c) LLM baseline did better).

| clip | audio | category | result | c outcome | pehchaan outcome | said |
|---|---|---|---|---|---|---|
| s001 | clean | in_kb | loss | unnecessary_question | ok | Hello, calling from Dr. Venkataramana's clinic in Kukatpally |
| s004 | clean | in_kb | win | ok | wrong_behaviour | Remind me to pick up medicines from Sri Venkateswara Pharmac |
| s007 | clean | in_kb | loss | entity_miss | ok | Call Srinivasan Iyer and wish him a happy birthday. |
| s017 | clean | in_kb | loss | wrong_action | ok | Book a cab from Kondapur to Rajiv Gandhi International Airpo |
| s020 | clean | in_kb | loss | wrong_behaviour | ok | Call Vijayalakshmi aunty and ask for the Dilsukhnagar addres |
| s088 | clean | control | loss | wrong_behaviour | ok | Wake me up at six thirty tomorrow morning. |
| s095 | clean | ambiguous | loss | wrong_behaviour | ok | Ask Harshil to send the invoice by Friday. |
| s098 | clean | ambiguous | loss | wrong_behaviour | ok | Remind me to send the project deck to Pranay before the clie |
| s103 | clean | ambiguous | loss | wrong_target | ok | Remind me to call Pranav tomorrow morning. |
| s106 | clean | context_mismatch | loss | wrong_target | ok | Book a table at Raju Hotel tomorrow at 9 AM. |
| s114 | clean | reference | loss | wrong_target | ok | Call my doctor, my tooth is paining. |
| s126 | clean | reference | loss | wrong_action | ok | Order Amma's tablets from the usual pharmacy. |
| s130 | clean | reference | loss | missed_clarification | ok | Ask my colleague to join the call. |
| s143 | clean | in_kb | loss | wrong_behaviour | ok | Remind me to call Anbuselvi about the Sunday cleaning. |
| s144 | clean | in_kb | loss | wrong_behaviour | ok | Tell Velu Anna to keep two cups of tea ready at 4 PM. |
| s146 | clean | in_kb | loss | wrong_target | ok | Message Nagaveni that we will visit on Sunday. |
| s151 | clean | in_kb | loss | wrong_behaviour | ok | Remind me to meet Gopikrishnan near Habsiguda at 7 PM. |
| s153 | clean | in_kb | loss | wrong_behaviour | ok | Remind me to wish Subhashis Chattopadhyay for Durga Puja. |
| s154 | clean | ambiguous | loss | wrong_behaviour | ok | Tell Swathi the college reunion is on Saturday. |
| s156 | clean | ambiguous | loss | wrong_target | ok | Remind me to call Anjali tomorrow. |
| s157 | clean | stale_default | loss | wrong_target | ok | Ask my driver to bring the cab to Koramangala at 9 AM. |
| s158 | clean | stale_default | loss | wrong_target | ok | Ask my accountant whether the income tax refund has come. |
| s161 | clean | reference | loss | wrong_target | ok | Ask my cousin to pick me up from the station. |
| s162 | clean | context_mismatch | loss | missed_clarification | ok | Order dinner from Hotel Subramanian tonight. |
| s163 | clean | context_mismatch | loss | wrong_target | ok | Get me a haircut slot at Venkatesh Salon on Sunday. |
| s004 | phone | in_kb | win | ok | wrong_behaviour | Remind me to pick up medicines from Sri Venkateswara Pharmac |
| s010 | phone | in_kb | loss | wrong_target | wrong_behaviour | Ravi Teja ko call karo, pucho Warangal pahunch gaya ya nahi. |
| s017 | phone | in_kb | loss | wrong_action | ok | Book a cab from Kondapur to Rajiv Gandhi International Airpo |
| s020 | phone | in_kb | loss | wrong_behaviour | ok | Call Vijayalakshmi aunty and ask for the Dilsukhnagar addres |
| s023 | phone | in_kb | win | ok | wrong_behaviour | Call Dr. Subramanian and move the root canal to Monday. |
| s033 | phone | in_kb | loss | wrong_behaviour | ok | Call Sreekumar Menon and tell him I land in Thiruvananthapur |
| s039 | phone | in_kb | loss | entity_miss | ok | Book the Diwali sweets order at Agarwal Mithai Bhandar in Ko |
| s052 | phone | in_kb | loss | wrong_behaviour | ok | Book a table at Jagannath Bhojanalaya for Sunday lunch. |
| s069 | phone | out_of_kb | loss | over_corrected | ok | Call Tejaswini and ask if she reached Nalgonda. |
| s088 | phone | control | loss | wrong_behaviour | ok | Wake me up at six thirty tomorrow morning. |
| s095 | phone | ambiguous | loss | unnecessary_question | ok | Ask Harshil to send the invoice by Friday. |
| s098 | phone | ambiguous | loss | wrong_behaviour | ok | Remind me to send the project deck to Pranay before the clie |
| s101 | phone | ambiguous | loss | wrong_target | ok | Call Harshit at 5. |
| s103 | phone | ambiguous | loss | wrong_target | ok | Remind me to call Pranav tomorrow morning. |
| s106 | phone | context_mismatch | loss | wrong_target | ok | Book a table at Raju Hotel tomorrow at 9 AM. |
| s114 | phone | reference | loss | wrong_target | ok | Call my doctor, my tooth is paining. |
| s123 | phone | reference | win | ok | wrong_behaviour | Nanna ki call cheyyi, BP tablets teesukunnara ani adugu. |
| s126 | phone | reference | loss | wrong_target | ok | Order Amma's tablets from the usual pharmacy. |
| s130 | phone | reference | loss | missed_clarification | ok | Ask my colleague to join the call. |
| s143 | phone | in_kb | loss | wrong_behaviour | ok | Remind me to call Anbuselvi about the Sunday cleaning. |
| s144 | phone | in_kb | loss | wrong_behaviour | ok | Tell Velu Anna to keep two cups of tea ready at 4 PM. |
| s145 | phone | in_kb | loss | entity_miss | ok | Remind me to call Puneeth Hegde about the cricket tickets. |
| s146 | phone | in_kb | loss | wrong_target | ok | Message Nagaveni that we will visit on Sunday. |
| s150 | phone | in_kb | loss | wrong_behaviour | ok | Call Itishree Mishra and ask about the exam results. |
| s151 | phone | in_kb | loss | wrong_behaviour | ok | Remind me to meet Gopikrishnan near Habsiguda at 7 PM. |
| s152 | phone | in_kb | loss | entity_miss | ok | Ask Sasmita Pattnaik to send the photos tonight. |
| s153 | phone | in_kb | loss | wrong_behaviour | ok | Remind me to wish Subhashis Chattopadhyay for Durga Puja. |
| s154 | phone | ambiguous | loss | wrong_behaviour | ok | Tell Swathi the college reunion is on Saturday. |
| s156 | phone | ambiguous | loss | wrong_target | ok | Remind me to call Anjali tomorrow. |
| s157 | phone | stale_default | loss | wrong_target | ok | Ask my driver to bring the cab to Koramangala at 9 AM. |
| s158 | phone | stale_default | loss | wrong_target | ok | Ask my accountant whether the income tax refund has come. |
| s161 | phone | reference | loss | wrong_target | ok | Ask my cousin to pick me up from the station. |
| s162 | phone | context_mismatch | loss | missed_clarification | ok | Order dinner from Hotel Subramanian tonight. |
