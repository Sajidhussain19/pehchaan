# Demo video

- **File:** [deliverables/Pehchaan_demo_full.mp4](deliverables/Pehchaan_demo_full.mp4)
- **Length:** 4 min 55 s (1920×1080, 30 fps, H.264 + AAC, with voice narration, 14.2 MB)
- **Live app:** https://d1rcvr2z1hg6u0.cloudfront.net
- **Code:** https://github.com/Sajidhussain19/pehchaan

## What it shows (in order)

| Time | Scene |
|---|---|
| 0:00 | **Title:** "AI assistants hear words. Pehchaan understands who you mean." |
| 0:05 | **The problem:** real mistakes from our own speech-to-text baseline: "Abids" → "in a bit", "Anjani" → "Aunt Johnny", "Thirumalai Selvan" → "the roomer life selvan". And no speech model knows who "my doctor" or "Amma" is. |
| 0:20 | **What Pehchaan is:** a personal-context layer between the transcript and the summary. It fixes names, resolves "my doctor", asks when unsure, and keeps unknown names as heard. |
| 0:35 | **How it works:** a hybrid AI system. Speech AI hears the request, sound matching against your contacts takes about 11 ms, then it decides: clue → default → ask. The LLM is used only for hard cases. |
| 0:55 | **The live app:** clips, typed text and the mic, with Pehchaan compared to a strong AI that has the same contacts. |
| 1:05 | **s067, misheard names:** "Padyalakshmi Jewelers in Punjabuta" → **Bhagyalakshmi Jewellers, Panjagutta**. The strong AI changed nothing. |
| 1:20 | **s104, knows when to ask:** two Rohits. The strong AI picked the wrong one; Pehchaan asks. |
| 1:34 | **s140, a clue beats the default:** "tooth filling" → the dentist, in 15 ms with no LLM call. |
| 1:45 | **s090, fixed in v2:** Telugu "ee roju" (*today*) is left alone (v1 had turned it into "Dr. Raju"). |
| 1:54 | **s101 (phone audio):** Harshit or Harshil? The strong AI guessed; Pehchaan lists the close matches and asks. |
| 2:04 | **A live typed request:** "Remind me to call my doctor about my tooth at 6 PM." The strong AI picked the family doctor; Pehchaan saved a reminder for **the dentist at 18:00** in 22 ms. |
| 2:20 | **The 5-step doctor demo:** book A → Dr. Venkataramana. Book B → Pehchaan asks. "Always use" → learned, only with consent. The same sentence again → no question. "…about my fever" → a clue still beats the saved choice. |
| 2:50 | **A saved reminder:** opened, showing how each name was resolved. |
| 2:58 | **Architecture:** browser → CloudFront → FastAPI on AWS EC2 → speech-to-text → LangGraph decision pipeline, with a GPT-4o-mini fallback and a SQLite reminder store. |
| 3:25 | **Built to fail safely:** if the AI is down it asks; the LLM can only pick real contacts; per-visitor reminders; rate limit and cost cap; 199 automated tests. |
| 3:45 | **Scoreboard, fresh held-out test-2:** wrong actions **10 → 2**, 25 wins / 62 ties / 3 losses, still worse on 4 unnecessary questions. Then the full metrics table. |
| 4:05 | **Results slide:** 10 → 2 wrong actions, 8 → 2 missed questions, 32/32 references, 11 ms median, about 80× cheaper. |
| 4:20 | **Known failure, shown on purpose (s185):** "Dhiraj" → "Dr. Raju", because the name list had only the spelling "Dheeraj". |
| 4:33 | **Limits and next steps.** |
| 4:50 | **Closing:** tagline, live link and repo. |

To reproduce every step yourself, follow the journeys in [AGENTS.md](AGENTS.md#7-end-to-end-journeys-in-the-browser).
