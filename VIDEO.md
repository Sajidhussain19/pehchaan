# Demo video

- **File:** [deliverables/Pehchaan_demo_full.mp4](deliverables/Pehchaan_demo_full.mp4)
- **Length:** 4 min 55 s (1920×1080, 30 fps, H.264 + AAC, with voice narration, 14.2 MB)
- **Live app:** https://d1rcvr2z1hg6u0.cloudfront.net
- **Code:** https://github.com/Sajidhussain19/pehchaan

## What it shows (in order)

1. **Title:** "AI assistants hear words. Pehchaan understands who you mean."
2. **The problem:** speech-to-text mishears Indian names, and no speech model knows who "my doctor" or "Amma" is.
3. **What Pehchaan is:** a layer after speech-to-text that resolves names and personal references against the user's own contacts.
4. **How it works:** sound-alike + fuzzy matching on the fast path, an LLM only when unsure, a question when two contacts fit.
5. **The live app:** contact book, demo clips, mic, typed text, and the Strong AI vs Pehchaan cards.
6. **Demo clips:**
   - **s067:** "Padyalakshmi Jewelers in Punjabuta" → **Bhagyalakshmi Jewellers, Panjagutta**, matched by sound.
   - **s104:** two Rohits. The strong AI guesses; Pehchaan asks.
   - **s140:** "my doctor … tooth filling" → the dentist, not the default family doctor.
   - **s090:** Telugu "ee roju" (*today*) is kept as heard (v1 had turned it into "Dr. Raju").
   - **s101 (phone audio):** Harshit or Harshil? Pehchaan lists the close matches and asks.
7. **A live typed request:** "Remind me to call my doctor about my tooth at 6 PM." → **Dr. Subramanian (dentist), 18:00**.
8. **The 5-step doctor demo:** same sentence, two users. Book A → Dr. Venkataramana. Book B → Pehchaan asks.
   "Always use" (learning only with consent) → learned. "…about my fever" → a clue still beats the saved choice.
9. **A saved reminder:** opened, with heard → resolved and how it was decided.
10. **Architecture:** how speech-to-text, matching, the decision pipeline, the knowledge base and the reminder store connect.
11. **Built to fail safely:** low confidence → ask or keep; OpenAI down → clips and typed sentences still work; budget and rate limits.
12. **Scoreboard:** fresh held-out test-2, wrong actions **10 → 2**, then the full metrics table.
13. **Results slide:** the summary of both held-out sets.
14. **Known failure, shown on purpose (s185):** "Dhiraj" → "Dr. Raju".
15. **Limits and next steps.**
16. **Closing:** the live link and the repo.

To reproduce every step yourself, follow the journeys in [AGENTS.md](AGENTS.md#7-end-to-end-journeys-in-the-browser).
