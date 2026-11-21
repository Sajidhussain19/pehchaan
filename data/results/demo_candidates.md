# Demo candidates (from the held-out test-2 run, Pehchaan v2)

Source: `data/results/report_test2_FINAL.json` (test-2 was frozen at tag `test2-frozen` before v2 ran on it). Overall, clip by clip, Pehchaan v2 vs (c): **win 25, tie 62, loss 3**.

Each clip below was picked because Pehchaan and baseline (c) diverge on **both** the clean and the phone recording. Everything is copied from the saved result files by `scripts/make_demo_candidates.py`.

## 1. s202: missed clarification

- **Said:** "Call Lakshmi tomorrow morning."
- **Expected:** clarify
- **Why it's a good demo:** Three contacts could be 'Lakshmi'. (c) silently picks the sister; Pehchaan asks which one.
- **clean** (`data/testset/audio/clean/s202.wav`), Pehchaan win:
  - heard: "Call Lakshmi tomorrow morning."
  - (c): RESOLVE, action target = Lakshmi Prasanna. "Lakshmi" -> Lakshmi Prasanna (The user referred to 'Lakshmi', which matches the contact 'Lakshmi Prasanna', who is the user's sister.)
  - Pehchaan: ASKS: Laxmi Devi or Lakshmi Narayanan or Lakshmi Prasanna? "Lakshmi" -> kept (clarify: 'Lakshmi' fits Laxmi Devi and Lakshmi Narayanan and Lakshmi Prasanna almost equally, and nothing in the sentence separates them)
- **phone** (`data/testset/audio/phone/s202.wav`), Pehchaan win:
  - heard: "Call Lakshmi tomorrow morning."
  - (c): RESOLVE, action target = Lakshmi Prasanna. "Lakshmi" -> Lakshmi Prasanna (The user referred to 'Lakshmi', which matches the contact 'Lakshmi Prasanna', who is the user's sister.)
  - Pehchaan: ASKS: Laxmi Devi or Lakshmi Narayanan or Lakshmi Prasanna? "Lakshmi" -> kept (clarify: 'Lakshmi' fits Laxmi Devi and Lakshmi Narayanan and Lakshmi Prasanna almost equally, and nothing in the sentence separates them)

## 2. s208: clue vs default

- **Said:** "Call my doctor to fix an appointment for my son's braces."
- **Expected:** resolve, target Dr. Subramanian
- **Why it's a good demo:** "braces" is a clue for the dentist. (c) uses the stale default (the family doctor).
- **clean** (`data/testset/audio/clean/s208.wav`), Pehchaan win:
  - heard: "Call my doctor to fix an appointment for my son's braces."
  - (c): RESOLVE, action target = Dr. Venkataramana. "my doctor" -> Dr. Venkataramana (The user referred to 'my doctor' which matches the default for doctor in their context.)
  - Pehchaan: RESOLVE, action target = Dr. Subramanian. "my doctor" -> Dr. Subramanian (resolve: clue 'braces' -> dentist)
- **phone** (`data/testset/audio/phone/s208.wav`), Pehchaan win:
  - heard: "Call my doctor to fix an appointment for my son's braces."
  - (c): RESOLVE, action target = Dr. Venkataramana. "my doctor" -> Dr. Venkataramana (The user referred to 'my doctor' which matches the default for doctor in their context.)
  - Pehchaan: RESOLVE, action target = Dr. Subramanian. "my doctor" -> Dr. Subramanian (resolve: clue 'braces' -> dentist)

## 3. s203: type mismatch

- **Said:** "Book a table at Arif Biryani Point tonight."
- **Expected:** clarify
- **Why it's a good demo:** 'Arif Biryani Point' isn't in the contacts, but Arif is the user's barber. (c) neither acts nor asks; Pehchaan asks before booking anything.
- **clean** (`data/testset/audio/clean/s203.wav`), Pehchaan win:
  - heard: "Book a table at Arif Biryani Point tonight."
  - (c): KEEP, no action target
  - Pehchaan: ASKS: Mohammed Arif? "Arif" -> kept (clarify: 'table' needs a business restaurant, but Mohammed Arif is your barber: asking instead of guessing); "Biryani" -> kept (keep: 'table' needs a business restaurant; Pranay Reddy doesn't fit)
- **phone** (`data/testset/audio/phone/s203.wav`), Pehchaan win:
  - heard: "Book a table at Arif Biryani Point tonight."
  - (c): KEEP, no action target
  - Pehchaan: ASKS: Mohammed Arif? "Arif" -> kept (clarify: 'table' needs a business restaurant, but Mohammed Arif is your barber: asking instead of guessing); "Biryani" -> kept (keep: 'table' needs a business restaurant; Pranay Reddy doesn't fit)

## 4. s199: near-identical contacts

- **Said:** "Text Ravi that I'll be late for dinner."
- **Expected:** clarify
- **Why it's a good demo:** Ravi Teja (cousin) and Ravi Tej (badminton partner). (c) guesses one; Pehchaan asks.
- **clean** (`data/testset/audio/clean/s199.wav`), Pehchaan win:
  - heard: "Text Ravi that I'll be late for dinner."
  - (c): RESOLVE, action target = Ravi Teja. "Ravi" -> Ravi Teja (Ravi is a cousin and the only Ravi in the user's contacts.)
  - Pehchaan: ASKS: Ravi Teja or Ravi Tej? "Ravi" -> kept (clarify: 'dinner' needs a business restaurant, but Ravi Teja is your cousin: asking instead of guessing)
- **phone** (`data/testset/audio/phone/s199.wav`), Pehchaan win:
  - heard: "Text Ravi that I'll be late for dinner."
  - (c): RESOLVE, action target = Ravi Teja. "Ravi" -> Ravi Teja (Ravi is a cousin and fits the context of a family dinner.)
  - Pehchaan: ASKS: Ravi Teja or Ravi Tej? "Ravi" -> kept (clarify: 'dinner' needs a business restaurant, but Ravi Teja is your cousin: asking instead of guessing)

## 5. s206: unfamiliar name

- **Said:** "Tell Anjana the cake order is confirmed."
- **Expected:** keep
- **Why it's a good demo:** 'Anjana' is a real name but not a contact. (c) messages Anjani (the tuition teacher); Pehchaan doesn't act.
- **clean** (`data/testset/audio/clean/s206.wav`), Pehchaan win:
  - heard: "Tell Anjana the cake order is confirmed."
  - (c): RESOLVE, action target = Anjani Mishra. "Anjana" -> Anjani Mishra (The name 'Anjana' closely resembles 'Anjani', who is the user's son's tuition teacher.)
  - Pehchaan: ASKS: Anjani Mishra or Dr. Ananthapadmanabhan or Anjali Verma? "Anjana" -> kept (clarify: 'cake' needs a business shop, but Anjani Mishra is your son's tuition teacher: asking instead of guessing)
- **phone** (`data/testset/audio/phone/s206.wav`), Pehchaan win:
  - heard: "Tell Anjana the cake order is confirmed."
  - (c): RESOLVE, action target = Anjani Mishra. "Anjana" -> Anjani Mishra (The name 'Anjana' closely resembles 'Anjani', who is the user's son's tuition teacher.)
  - Pehchaan: ASKS: Anjani Mishra or Dr. Ananthapadmanabhan or Anjali Verma? "Anjana" -> kept (clarify: 'cake' needs a business shop, but Anjani Mishra is your son's tuition teacher: asking instead of guessing)

## Honest failure: s185: wrong target (an honest failure that still exists in v2)

- **Said:** "Tell Dheeraj to bring the projector to the Shadnagar office."
- **Expected:** keep
- **Why it's a good demo:** Clean audio: speech-to-text wrote "Dhiraj", which sounds like "Dr. Raju" (0.84), and "Dhiraj" is not in our list of common first names, so Pehchaan v2 links it to Dr. Raju. (c) correctly keeps it. On phone audio v2 gets it right. Over-correction on test-2: v2 2/36, v1 5/36, (c) 3/36.
- **clean** (`data/testset/audio/clean/s185.wav`), Pehchaan loss:
  - heard: "Tell Dhiraj to bring the projector to the Shadnagar office."
  - (c): KEEP, no action target. "Dhiraj" -> kept (Dhiraj is not in the user's contacts.); "Shadnagar" -> kept (Shadnagar is a known place but not in the user's context.)
  - Pehchaan: CORRECT, action target = Dr. Raju. "Dhiraj" -> Dr. Raju (resolve: sounds like Dr. Raju (0.84), clear lead of 0.21); "Shadnagar" -> kept (keep: LLM: The phrase 'Shadnagar' refers to a specific location that is not among the candidates provided. The candidates are unrelated places.)
- **phone** (`data/testset/audio/phone/s185.wav`), Pehchaan win:
  - heard: "Tell Viraj to bring the projector to the Shadnagar office."
  - (c): KEEP, no action target. "Viraj" -> kept (Viraj is not in the user's contacts.); "Shadnagar" -> Hyderabad (Shadnagar is a known locality, but not explicitly listed in the context.)
  - Pehchaan: KEEP, no action target. "Viraj" -> kept (keep: LLM: The name 'Viraj' does not match any of the candidates provided.); "Shadnagar" -> kept (keep: LLM: The name 'Shadnagar' does not match any of the candidates provided.)
