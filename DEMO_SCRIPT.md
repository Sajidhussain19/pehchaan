# Backup demo recording: 2 minutes, captions instead of voice

Pehchaan is **a hybrid AI system: speech AI on every voice request (demo clips replay their saved transcripts), LLM reasoning only for hard cases.** Most requests are decided on the fast path (sound matching + your personal context, no LLM call needed).

**Purpose:** if the live demo fails (Wi-Fi, AWS, mic), play this screen recording. Record it at **1280×800**,
browser zoom 100%, on `http://localhost:8000`. Use any screen recorder (Windows: Win+Alt+R with Xbox Game Bar, or OBS).
Add the captions afterwards as text overlays (Clipchamp/OBS), large and bottom-centred, one at a time.

**Before recording**
1. `uvicorn app.main:app --port 8000`, then open http://localhost:8000.
2. Click **Reset demo** (top right), confirm. Contact book: **Full contacts**. "Compare with strong AI": **on**. Audio: **Clean**.
3. Close other tabs and notifications.

The first four clips are your rehearsed ones, from the **original test set**. The page labels that group
"Original test set (seen before v2)": v2's fixes were designed after looking at v1's mistakes there, so those
clips show the system working, and **test-2 on the scoreboard is the clean proof**. Every clip replays the saved
evaluation transcript and both systems' saved decisions, so what you record is exactly what the scoreboard counts.

| Time | Click / do | On-screen caption |
|---|---|---|
| 0:00–0:06 | Show the page, still | **Speech-to-text hears words. It doesn't know *your* contacts.** Pehchaan: speech AI on every voice request (demo clips replay their saved transcripts), LLM reasoning only for hard cases. |
| 0:06–0:22 | Clips → **s104 · missed clarification — Rohit vs Rohith** → **▶ Play** (let it play), then **Run** | "Call Rohit at 6 PM." You have **two** Rohits. |
| | Point at the cards and the question panel | Strong AI **guesses** Rohith Reddy: **✗ Wrong target**. Pehchaan **asks**: Rohit Chaturvedi or Rohith Reddy? **✓ Correct** |
| 0:22–0:38 | **s140 · clue vs default — tooth → dentist** → **Run** | "…ask my doctor about the **tooth filling** on Friday." |
| | Click the "my doctor" highlight in the Pehchaan card to open *why* | Strong AI uses the default family doctor: **✗**. Pehchaan: clue **"tooth" → Dr. Subramanian, the dentist**. **✓** |
| 0:38–0:50 | **s067 · misheard name — Bhagyalakshmi Jewellers, Panjagutta** → **Run** | Speech-to-text wrote "**Padyalakshmi Jewelers in Punjabuta**". |
| | Point at the Pehchaan highlights | Strong AI changes nothing: **✗**. Pehchaan fixes both by sound: **Bhagyalakshmi Jewellers**, **Panjagutta**, in ~13 ms on the fast path (no LLM call needed). **✓** |
| 0:50–1:00 | **s090 · v1 failure — fixed in v2** → **Run** | Telugu "ee **roju**" = "today". v1 turned it into "Dr. Raju". **v2 keeps it: everyday speech, not a name.** ✓ |
| 1:00–1:04 | Click **▶ Demo mode** → **Start** | **Same sentence, two different users.** |
| 1:04–1:10 | **Next** (step 1, book A) | User A has one doctor → reminder for **Dr. Venkataramana**. |
| 1:10–1:17 | **Next** (step 2, book B) | User B has two doctors, no default → Pehchaan **asks**. Show what the Strong AI card actually returned, or its comparison status. |
| 1:17–1:23 | **Next** (step 3: "Always use Dr. Subramanian") | Learned **only with consent**: "Always use" (vs "Use this time"). |
| 1:23–1:28 | **Next** (step 4) | Same sentence again → resolved from the **learned preference**. |
| 1:28–1:33 | **Next** (step 5: "…about my fever") | A clue still wins: **"fever" → the GP**, not the saved dentist. |
| 1:33–1:36 | Click a reminder on the right | Real saved reminders: person, role, time, heard → resolved, how it was decided. |
| 1:36–1:43 | Tab **Scoreboard** (top table) | **v1, 220 held-out clips, run once.** Wrong target **11 vs 24**. Weak spot: over-correction **11 vs 3**. |
| 1:43–1:50 | Scroll to **"v2 fix, proven on a fresh held-out set"** | **Fresh test-2, frozen before v2 ran:** over-correction **2 vs 3**, wrong target **2 vs 10**. Still "Worse": 4 unnecessary questions. |
| 1:50–1:58 | Tab **Live demo**, scroll the clips list to **s185 · Known failure (v2)** → **Run** | Known failure in v2: "**Dhiraj**" became "**Dr. Raju**". Strong AI: ✓. We show it. |
| 1:58–2:00 | Still | **Pehchaan: AI assistants hear words. Pehchaan understands who you mean.** |

**Tips**
- If a step looks slow, cut the waiting in the editor. Never speed up the timings that are shown on screen.
- Live mic (optional extra take, not in the 2 minutes): tap **Tap to record**, say "Remind me to call my doctor about
  my tooth at 6 PM", tap again. It shows real speech-to-text time and cost.
