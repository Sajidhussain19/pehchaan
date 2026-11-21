# Backup demo recording: 2 minutes, captions instead of voice

**Purpose:** if the live demo fails (Wi-Fi, AWS, mic), play this screen recording. Record it at **1280×800**,
browser zoom 100%, on `http://localhost:8000`. Use any screen recorder (Windows: Win+Alt+R with Xbox Game Bar, or OBS).
Add the captions afterwards as text overlays (Clipchamp/OBS), large and bottom-centred, one at a time.

**Before recording**
1. `uvicorn app.main:app --port 8000`, then open http://localhost:8000.
2. Click **Reset demo** (top right), confirm. Contact book: **Full contacts**. "Compare with strong AI": **on**. Audio: **Clean**.
3. Close other tabs and notifications.

Demo clips (from test-2, Pehchaan v2) use the saved evaluation transcript and the strong AI's saved answer, so what you
record is exactly what the scoreboard counts.

| Time | Click / do | On-screen caption |
|---|---|---|
| 0:00–0:08 | Show the page, still | **Speech-to-text hears words. It doesn't know *your* contacts.** |
| 0:08–0:12 | Hover the two cards | Left: a strong AI (GPT-4o-mini + the same contacts). Right: Pehchaan. |
| 0:12–0:30 | Clips list → **s202 · Missed clarification** → **▶ Play** (let it play), then **Run** | "Call Lakshmi tomorrow morning." You have **three** Lakshmis. |
| | Point at the cards | Strong AI **guesses** your sister: **✗ Wrong target**. Pehchaan **asks** which Lakshmi. **✓ Correct** |
| 0:30–0:48 | **s208 · Clue vs default** → **Run** | "Call my doctor to fix an appointment for my son's **braces**." |
| | Click the "my doctor" highlight in the Pehchaan card to open *why* | Strong AI picks the default family doctor. Pehchaan: clue **"braces" → the dentist**, with the reason shown. |
| 0:48–1:02 | **s206 · Unfamiliar name** → **Run** | "Tell **Anjana** the cake order is confirmed." Anjana is NOT a contact. |
| | Point at the cards | Strong AI messages **Anjani** (the tuition teacher): **✗ Wrong target**. Pehchaan doesn't act on a stranger. |
| 1:02–1:08 | Click **▶ Demo mode** → **Start** | **Same sentence, two different users.** |
| 1:08–1:14 | **Next** (step 1, book A) | User A has one doctor → reminder for **Dr. Venkataramana**. |
| 1:14–1:22 | **Next** (step 2, book B) | User B has two doctors, no default → Pehchaan **asks**. The strong AI guesses. |
| 1:22–1:30 | **Next** (step 3: "Always use Dr. Subramanian") | Learned **only with consent**: "Always use" (vs "Use this time"). |
| 1:30–1:36 | **Next** (step 4) | Same sentence again → resolved from the **learned preference**. |
| 1:36–1:42 | **Next** (step 5: "…about my fever") | A clue still wins: **"fever" → the GP**, not the saved dentist. |
| 1:42–1:44 | Click a reminder on the right | Real saved reminders: person, role, time, heard → resolved, how it was decided. |
| 1:44–1:50 | Tab **Scoreboard** (top table) | **v1, 220 held-out clips, run once.** Wrong target **11 vs 24**. Weak spot: over-correction **11 vs 3**. |
| 1:50–1:56 | Scroll to **"v2 fix, proven on a fresh held-out set"** | **Fresh test-2, frozen before v2 ran:** over-correction **2 vs 3**, wrong target **2 vs 10**. Still "Worse": 4 unnecessary questions. |
| 1:56–2:00 | Tab **Live demo**, audio **Clean**, **s185 · Known failure** → **Run** | Known failure in v2: "**Dhiraj**" became "**Dr. Raju**". Strong AI: ✓. We show it. |
| 2:00 | Still | **Pehchaan: AI assistants hear words. Pehchaan understands who you mean.** |

**Tips**
- If a step looks slow, cut the waiting in the editor. Never speed up the timings that are shown on screen.
- Live mic (optional extra take, not in the 2 minutes): tap **Tap to record**, say "Remind me to call my doctor about
  my tooth at 6 PM", tap again. It shows real speech-to-text time and cost.
