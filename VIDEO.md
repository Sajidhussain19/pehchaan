# Demo video

- **File:** [deliverables/Pehchaan_demo_voice.mp4](deliverables/Pehchaan_demo_voice.mp4)
- **Length:** 2 min 58 s (1920×1080, 30 fps, H.264 + AAC, with voice narration, 9.3 MB)
- **Live app:** https://d1rcvr2z1hg6u0.cloudfront.net
- **Code:** https://github.com/Sajidhussain19/pehchaan

## What it shows (in order)

1. **Title:** "AI assistants hear words. Pehchaan understands who you mean."
2. **The problem:** real mistakes from our own speech-to-text baseline, e.g. "Abids" heard as "in a bit",
   "Thirumalai Selvan" as "the roomer life selvan". No speech model knows who "my doctor" or "Amma" is.
3. **The live app:** a layer for AI call assistants: contact book, demo clips, mic, typed text, the Strong AI vs Pehchaan cards.
4. **s067, misheard names:** "Padyalakshmi Jewelers in Punjabuta" → **Bhagyalakshmi Jewellers, Panjagutta**, matched by sound.
   The strong AI changed nothing.
5. **s104, knows when to ask:** two Rohits. The strong AI guessed Rohith Reddy; Pehchaan asks.
6. **s140, a clue beats the default:** "my doctor … tooth filling" → the dentist, not the family doctor, in 15 ms with no LLM call.
7. **s090, fixed in v2:** Telugu "ee roju" (*today*) is kept as heard; v1 had turned it into "Dr. Raju".
8. **s101 (phone audio):** Harshit or Harshil? The strong AI guessed; Pehchaan lists the close matches and asks.
9. **The 5-step doctor demo:** same sentence, two users. Book A → Dr. Venkataramana; book B → asks; "Always use"
   (learning only with consent) → learned; "…about my fever" → a clue still beats the saved choice.
10. **Nothing is hidden:** a saved reminder opened, with heard → resolved and how it was decided.
11. **Proof on fresh held-out data (test-2):** wrong actions **10 → 2**, 25 wins / 62 ties / 3 losses.
    Still worse: 4 unnecessary questions vs 0.
12. **Known failure, shown on purpose (s185):** "Dhiraj" → "Dr. Raju".
13. **Close:** the live link and the repo. Fictional contacts, synthetic and real Indian-accented voices, built solo with AI coding agents.

To reproduce every step yourself, follow the journeys in [AGENTS.md](AGENTS.md#7-end-to-end-journeys-in-the-browser).
