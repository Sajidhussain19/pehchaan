# Pehchaan evaluation: test split, audio = all

**v2 on original test (already seen — not a clean held-out result). v2's fixes were designed after looking at v1's losses on this set.**

Generated 2026-11-21T19:06:44. Systems: (c) LLM baseline, Pehchaan v1, Pehchaan v2.

Every number is shown with raw counts. A clarify decision takes no action until the user answers.

### Overall: transcript metrics

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 109/148 = 74% | 118/148 = 80% | 130/148 = 88% |
| wer | 292/2392 = 12% | 265/2392 = 11% | 248/2392 = 10% |
| over_correction_rate | 3/70 = 4% | 11/70 = 16% | 4/70 = 6% |

### Overall: decision metrics (systems that make decisions)

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| behaviour_accuracy | 162/220 = 74% | 182/220 = 83% | 201/220 = 91% |
| exact_action_target_accuracy | 74/118 = 63% | 96/118 = 81% | 102/118 = 86% |
| time_accuracy | 18/20 = 90% | 18/20 = 90% | 18/20 = 90% |
| wrong_target_rate | 24/220 = 11% | 11/220 = 5% | 8/220 = 4% |
| unnecessary_question_rate | 0/198 = 0% | 15/198 = 8% | 5/198 = 3% |
| missed_clarification_rate | 14/14 = 100% | 1/14 = 7% | 1/14 = 7% |
| clarify_candidates_ok | 0/0 = n/a | 9/13 = 69% | 9/13 = 69% |
| reference_resolution_accuracy | 19/32 = 59% | 32/32 = 100% | 32/32 = 100% |
| no_llm_rate | 0/220 = 0% | 191/220 = 87% | 191/220 = 87% |
| latency_ms_mean | 1548.5 | 170.0 | 320.9 |
| latency_ms_median | 1502.4 | 9.4 | 10.3 |
| cost_usd_mean | 0.000972 | 1.2e-05 | 1.4e-05 |

### Audio = clean

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 53/74 = 72% | 58/74 = 78% | 64/74 = 86% |
| wer | 114/1019 = 11% | 118/1019 = 12% | 109/1019 = 11% |
| over_correction_rate | 2/22 = 9% | 6/22 = 27% | 3/22 = 14% |
| behaviour_accuracy | 69/97 = 71% | 78/97 = 80% | 87/97 = 90% |
| exact_action_target_accuracy | 38/59 = 64% | 47/59 = 80% | 50/59 = 85% |
| time_accuracy | 9/10 = 90% | 8/10 = 80% | 8/10 = 80% |
| wrong_target_rate | 12/97 = 12% | 6/97 = 6% | 5/97 = 5% |
| unnecessary_question_rate | 0/86 = 0% | 8/86 = 9% | 3/86 = 3% |
| missed_clarification_rate | 7/7 = 100% | 0/7 = 0% | 0/7 = 0% |
| clarify_candidates_ok | 0/0 = n/a | 5/7 = 71% | 5/7 = 71% |
| reference_resolution_accuracy | 10/16 = 62% | 16/16 = 100% | 16/16 = 100% |

### Audio = phone

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 56/74 = 76% | 60/74 = 81% | 66/74 = 89% |
| wer | 122/1019 = 12% | 116/1019 = 11% | 108/1019 = 11% |
| over_correction_rate | 1/22 = 5% | 5/22 = 23% | 1/22 = 5% |
| behaviour_accuracy | 67/97 = 69% | 78/97 = 80% | 88/97 = 91% |
| exact_action_target_accuracy | 36/59 = 61% | 49/59 = 83% | 52/59 = 88% |
| time_accuracy | 9/10 = 90% | 10/10 = 100% | 10/10 = 100% |
| wrong_target_rate | 12/97 = 12% | 5/97 = 5% | 3/97 = 3% |
| unnecessary_question_rate | 0/86 = 0% | 7/86 = 8% | 2/86 = 2% |
| missed_clarification_rate | 7/7 = 100% | 1/7 = 14% | 1/7 = 14% |
| clarify_candidates_ok | 0/0 = n/a | 4/6 = 67% | 4/6 = 67% |
| reference_resolution_accuracy | 9/16 = 56% | 16/16 = 100% | 16/16 = 100% |

### Audio = real

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 56/354 = 16% | 31/354 = 9% | 31/354 = 9% |
| over_correction_rate | 0/26 = 0% | 0/26 = 0% | 0/26 = 0% |
| behaviour_accuracy | 26/26 = 100% | 26/26 = 100% | 26/26 = 100% |
| exact_action_target_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | 0/26 = 0% | 0/26 = 0% | 0/26 = 0% |
| unnecessary_question_rate | 0/26 = 0% | 0/26 = 0% | 0/26 = 0% |
| missed_clarification_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = ambiguous

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 6/8 = 75% | 7/8 = 88% | 5/8 = 62% |
| wer | 18/124 = 15% | 17/124 = 14% | 21/124 = 17% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | 8/14 = 57% | 10/14 = 71% | 10/14 = 71% |
| exact_action_target_accuracy | 8/8 = 100% | 7/8 = 88% | 5/8 = 62% |
| time_accuracy | 2/2 = 100% | 1/2 = 50% | 1/2 = 50% |
| wrong_target_rate | 5/14 = 36% | 0/14 = 0% | 0/14 = 0% |
| unnecessary_question_rate | 0/8 = 0% | 0/8 = 0% | 0/8 = 0% |
| missed_clarification_rate | 6/6 = 100% | 1/6 = 17% | 1/6 = 17% |
| clarify_candidates_ok | 0/0 = n/a | 3/5 = 60% | 3/5 = 60% |
| reference_resolution_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = context_mismatch

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 4/120 = 3% | 6/120 = 5% | 6/120 = 5% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | 6/10 = 60% | 10/10 = 100% | 10/10 = 100% |
| exact_action_target_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | 4/10 = 40% | 0/10 = 0% | 0/10 = 0% |
| unnecessary_question_rate | 0/6 = 0% | 0/6 = 0% | 0/6 = 0% |
| missed_clarification_rate | 4/4 = 100% | 0/4 = 0% | 0/4 = 0% |
| clarify_candidates_ok | 0/0 = n/a | 2/4 = 50% | 2/4 = 50% |
| reference_resolution_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = control

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 11/170 = 6% | 29/170 = 17% | 29/170 = 17% |
| over_correction_rate | 0/18 = 0% | 2/18 = 11% | 0/18 = 0% |
| behaviour_accuracy | 18/18 = 100% | 16/18 = 89% | 18/18 = 100% |
| exact_action_target_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | 0/18 = 0% | 0/18 = 0% | 0/18 = 0% |
| unnecessary_question_rate | 0/18 = 0% | 0/18 = 0% | 0/18 = 0% |
| missed_clarification_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = in_kb

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 97/134 = 72% | 105/134 = 78% | 119/134 = 89% |
| wer | 137/1080 = 13% | 118/1080 = 11% | 99/1080 = 9% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | 54/94 = 57% | 71/94 = 76% | 83/94 = 88% |
| exact_action_target_accuracy | 47/82 = 57% | 63/82 = 77% | 71/82 = 87% |
| time_accuracy | 14/14 = 100% | 13/14 = 93% | 13/14 = 93% |
| wrong_target_rate | 2/94 = 2% | 2/94 = 2% | 2/94 = 2% |
| unnecessary_question_rate | 0/94 = 0% | 15/94 = 16% | 5/94 = 5% |
| missed_clarification_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = out_of_kb

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 26/172 = 15% | 37/172 = 22% | 35/172 = 20% |
| over_correction_rate | 1/18 = 6% | 5/18 = 28% | 2/18 = 11% |
| behaviour_accuracy | 18/18 = 100% | 13/18 = 72% | 16/18 = 89% |
| exact_action_target_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | 2/2 = 100% | 2/2 = 100% | 2/2 = 100% |
| wrong_target_rate | 0/18 = 0% | 5/18 = 28% | 2/18 = 11% |
| unnecessary_question_rate | 0/18 = 0% | 0/18 = 0% | 0/18 = 0% |
| missed_clarification_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = real_speech

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 56/354 = 16% | 31/354 = 9% | 31/354 = 9% |
| over_correction_rate | 0/26 = 0% | 0/26 = 0% | 0/26 = 0% |
| behaviour_accuracy | 26/26 = 100% | 26/26 = 100% | 26/26 = 100% |
| exact_action_target_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | 0/26 = 0% | 0/26 = 0% | 0/26 = 0% |
| unnecessary_question_rate | 0/26 = 0% | 0/26 = 0% | 0/26 = 0% |
| missed_clarification_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

### Category = reference

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 6/6 = 100% | 6/6 = 100% | 6/6 = 100% |
| wer | 23/230 = 10% | 15/230 = 7% | 15/230 = 7% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | 22/28 = 79% | 28/28 = 100% | 28/28 = 100% |
| exact_action_target_accuracy | 19/24 = 79% | 22/24 = 92% | 22/24 = 92% |
| time_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | 7/28 = 25% | 2/28 = 7% | 2/28 = 7% |
| unnecessary_question_rate | 0/24 = 0% | 0/24 = 0% | 0/24 = 0% |
| missed_clarification_rate | 4/4 = 100% | 0/4 = 0% | 0/4 = 0% |
| clarify_candidates_ok | 0/0 = n/a | 4/4 = 100% | 4/4 = 100% |
| reference_resolution_accuracy | 19/28 = 68% | 28/28 = 100% | 28/28 = 100% |

### Category = stale_default

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 4/52 = 8% | 0/52 = 0% | 0/52 = 0% |
| over_correction_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| behaviour_accuracy | 4/4 = 100% | 4/4 = 100% | 4/4 = 100% |
| exact_action_target_accuracy | 0/4 = 0% | 4/4 = 100% | 4/4 = 100% |
| time_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wrong_target_rate | 4/4 = 100% | 0/4 = 0% | 0/4 = 0% |
| unnecessary_question_rate | 0/4 = 0% | 0/4 = 0% | 0/4 = 0% |
| missed_clarification_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | 0/4 = 0% | 4/4 = 100% | 4/4 = 100% |

### Category = unfamiliar_near_match

| metric | (c) LLM baseline | Pehchaan v1 | Pehchaan v2 |
|---|---|---|---|
| entity_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| wer | 13/90 = 14% | 12/90 = 13% | 12/90 = 13% |
| over_correction_rate | 2/8 = 25% | 4/8 = 50% | 2/8 = 25% |
| behaviour_accuracy | 6/8 = 75% | 4/8 = 50% | 6/8 = 75% |
| exact_action_target_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| time_accuracy | 0/2 = 0% | 2/2 = 100% | 2/2 = 100% |
| wrong_target_rate | 2/8 = 25% | 2/8 = 25% | 2/8 = 25% |
| unnecessary_question_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| missed_clarification_rate | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| clarify_candidates_ok | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |
| reference_resolution_accuracy | 0/0 = n/a | 0/0 = n/a | 0/0 = n/a |

## Clip by clip: Pehchaan v2 vs (c) LLM baseline

**Pehchaan v2 wins 58, ties 155, loses 7** (of 220 clips; win = Pehchaan v2 did better).

| clip | audio | category | result | v2 outcome | c outcome | said |
|---|---|---|---|---|---|---|
| s011 | clean | in_kb | win | ok | wrong_behaviour | Tell Ravi Tej I'll skip badminton on Sunday. |
| s012 | clean | in_kb | win | ok | wrong_behaviour | Book an appointment with Dr. Ananthapadmanabhan for next Tue |
| s016 | clean | in_kb | win | ok | entity_miss | Hitech City lo traffic ela undi? I need to reach Nanakramgud |
| s021 | clean | in_kb | win | ok | wrong_behaviour | Remind me to take mom to Dr. Prameela Rani on Friday at 11. |
| s027 | clean | in_kb | win | ok | wrong_behaviour | Book a table at Chettinad Spice Kitchen in Velachery for Sun |
| s028 | clean | in_kb | win | ok | wrong_behaviour | Call Manjunath Gowda and fix the cab to Koramangala for 6 PM |
| s031 | clean | in_kb | win | ok | wrong_behaviour | Book a table at Udupi Krishna Bhavan in Basavanagudi for bre |
| s037 | clean | in_kb | win | ok | entity_miss | Laxmi Devi ko bolo kal subah nahi aana hai. |
| s045 | clean | in_kb | win | ok | wrong_behaviour | Message Gurpreet Singh to pick me up from Amritsar station a |
| s048 | clean | in_kb | win | ok | wrong_behaviour | Remind me to call Bhavesh Thakkar about the gold chain on Sa |
| s050 | clean | in_kb | win | ok | wrong_behaviour | Call Shree Ambica Khakhra House in Ahmedabad and order two b |
| s051 | clean | in_kb | win | ok | wrong_behaviour | Message Debasish Mohapatra that I'll reach Bhubaneswar on Fr |
| s057 | clean | in_kb | win | entity_miss | wrong_target | Shaik Khaja Moinuddin ko bolo AC service Sunday ko karna hai |
| s058 | clean | in_kb | win | ok | entity_miss | Remind me to buy mutton from Naseeruddin Qureshi on Saturday |
| s061 | clean | in_kb | win | ok | wrong_behaviour | Message Fr. Anthony Raj that choir practice is at 6 on Satur |
| s066 | clean | in_kb | loss | wrong_target | wrong_action | Kukatpally nunchi Begumpet ki auto book cheyyi. |
| s067 | clean | in_kb | win | ok | wrong_behaviour | Call Bhagyalakshmi Jewellers in Panjagutta and ask if the ea |
| s068 | clean | in_kb | win | ok | wrong_action | Remind me to visit Padmavathi Nursing Home in Malakpet at 4  |
| s081 | clean | out_of_kb | loss | wrong_target | ok | Book a table at Mayuri Darshini in Shivamogga for lunch. |
| s100 | clean | ambiguous | loss | wrong_behaviour | ok | Call Anjani and ask if maths tuition is on this evening. |
| s102 | clean | ambiguous | win | ok | wrong_target | Send a message to Sai, I'll reach in 10 minutes. |
| s104 | clean | ambiguous | win | ok | wrong_target | Call Rohit at 6 PM. |
| s105 | clean | ambiguous | win | ok | wrong_target | Message Swathi that I'm running late. |
| s107 | clean | context_mismatch | win | ok | wrong_target | Book a table at Sharma Ji Dhaba for tonight. |
| s108 | clean | context_mismatch | win | ok | wrong_target | Book a table at Venkataramana Restaurant for Sunday lunch. |
| s116 | clean | reference | win | ok | wrong_behaviour | Ask my colleague to send the invoice before Friday. |
| s125 | clean | reference | win | ok | wrong_target | Bhaiya ko bolo Diwali pe ghar aa jaye. |
| s129 | clean | reference | loss | wrong_target | ok | Remind me to take Nanna to Dr. Ananthapadmanabhan on Tuesday |
| s131 | clean | reference | win | ok | wrong_target | Call the electrician, the fan is not working. |
| s132 | clean | reference | win | ok | wrong_target | Call my son's teacher. |
| s140 | clean | stale_default | win | ok | wrong_target | Remind me to ask my doctor about the tooth filling on Friday |
| s141 | clean | stale_default | win | ok | wrong_target | Remind me to send the sales numbers to my manager before the |
| s012 | phone | in_kb | win | ok | wrong_behaviour | Book an appointment with Dr. Ananthapadmanabhan for next Tue |
| s016 | phone | in_kb | win | ok | entity_miss | Hitech City lo traffic ela undi? I need to reach Nanakramgud |
| s019 | phone | in_kb | win | ok | wrong_behaviour | Message Lakshmi Prasanna that I'll come to Secunderabad on S |
| s021 | phone | in_kb | win | ok | wrong_behaviour | Remind me to take mom to Dr. Prameela Rani on Friday at 11. |
| s027 | phone | in_kb | win | ok | wrong_action | Book a table at Chettinad Spice Kitchen in Velachery for Sun |
| s031 | phone | in_kb | win | ok | wrong_behaviour | Book a table at Udupi Krishna Bhavan in Basavanagudi for bre |
| s032 | phone | in_kb | win | ok | entity_miss | Message Unnikrishnan Nair that the design review is at 4 PM. |
| s034 | phone | in_kb | win | ok | wrong_behaviour | Remind me to call Jayalakshmi Warrier about the music class  |
| s037 | phone | in_kb | win | ok | entity_miss | Laxmi Devi ko bolo kal subah nahi aana hai. |
| s045 | phone | in_kb | win | ok | wrong_behaviour | Message Gurpreet Singh to pick me up from Amritsar station a |
| s047 | phone | in_kb | loss | wrong_target | wrong_behaviour | Book a table at Sher-e-Punjab Dhaba in Gachibowli for tonigh |
| s048 | phone | in_kb | win | ok | wrong_behaviour | Remind me to call Bhavesh Thakkar about the gold chain on Sa |
| s050 | phone | in_kb | win | ok | wrong_behaviour | Call Shree Ambica Khakhra House in Ahmedabad and order two b |
| s051 | phone | in_kb | win | ok | wrong_behaviour | Message Debasish Mohapatra that I'll reach Bhubaneswar on Fr |
| s057 | phone | in_kb | win | entity_miss | wrong_target | Shaik Khaja Moinuddin ko bolo AC service Sunday ko karna hai |
| s058 | phone | in_kb | win | ok | entity_miss | Remind me to buy mutton from Naseeruddin Qureshi on Saturday |
| s060 | phone | in_kb | win | ok | entity_miss | Call Moazzam Book House in Abids and ask if the novel is in  |
| s064 | phone | in_kb | win | ok | wrong_action | Remind me to pick up the cake from Al Noor Bakery in Yousufg |
| s067 | phone | in_kb | win | ok | wrong_behaviour | Call Bhagyalakshmi Jewellers in Panjagutta and ask if the ea |
| s097 | phone | ambiguous | win | ok | entity_miss | Message Rohith to check when my car service will be done. |
| s100 | phone | ambiguous | loss | wrong_behaviour | ok | Call Anjani and ask if maths tuition is on this evening. |
| s104 | phone | ambiguous | win | ok | wrong_target | Call Rohit at 6 PM. |
| s105 | phone | ambiguous | win | ok | wrong_target | Message Swathi that I'm running late. |
| s107 | phone | context_mismatch | win | ok | wrong_target | Book a table at Sharma Ji Dhaba for tonight. |
| s108 | phone | context_mismatch | win | ok | wrong_target | Book a table at Venkataramana Restaurant for Sunday lunch. |
| s116 | phone | reference | win | ok | wrong_target | Ask my colleague to send the invoice before Friday. |
| s124 | phone | reference | win | ok | wrong_behaviour | Message Akka that I'll come to Secunderabad on Saturday. |
| s125 | phone | reference | win | ok | wrong_target | Bhaiya ko bolo Diwali pe ghar aa jaye. |
| s129 | phone | reference | loss | wrong_target | ok | Remind me to take Nanna to Dr. Ananthapadmanabhan on Tuesday |
| s131 | phone | reference | win | ok | wrong_target | Call the electrician, the fan is not working. |
| s132 | phone | reference | win | ok | wrong_target | Call my son's teacher. |
| s140 | phone | stale_default | win | ok | wrong_target | Remind me to ask my doctor about the tooth filling on Friday |
| s141 | phone | stale_default | win | ok | wrong_target | Remind me to send the sales numbers to my manager before the |
