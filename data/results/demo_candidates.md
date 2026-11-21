# Demo candidates (from the FINAL held-out test run)

Source: `data/results/report_test_FINAL.json`. Overall, clip by clip, Pehchaan vs (c): **win 49, tie 149, loss 22**.

Each clip below was picked because Pehchaan and baseline (c) diverge on **both** the clean and the phone recording. Everything is copied from the saved result files by `scripts/make_demo_candidates.py`.

## 1. s104: missed clarification

- **Said:** "Call Rohit at 6 PM."
- **Expected:** clarify
- **Why it's a good demo:** Two contacts are called Rohit/Rohith. (c) silently picks one; Pehchaan asks which one.
- **clean** (`data/testset/audio/clean/s104.wav`), Pehchaan win:
  - heard: "Call Rohit at 6 p.m."
  - (c): RESOLVE, action target = Rohith Reddy. "Rohit" -> Rohith Reddy (Rohit is a saved contact, and the context indicates he is the car service advisor.)
  - Pehchaan: ASKS: Rohit Chaturvedi or Rohith Reddy? "Rohit" -> kept (clarify: 'Rohit' fits Rohit Chaturvedi and Rohith Reddy almost equally, and nothing in the sentence separates them)
- **phone** (`data/testset/audio/phone/s104.wav`), Pehchaan win:
  - heard: "Call Rohit at 6 p.m."
  - (c): RESOLVE, action target = Rohith Reddy. "Rohit" -> Rohith Reddy (Rohit is a saved contact, and the context indicates he is a car service advisor.)
  - Pehchaan: ASKS: Rohit Chaturvedi or Rohith Reddy? "Rohit" -> kept (clarify: 'Rohit' fits Rohit Chaturvedi and Rohith Reddy almost equally, and nothing in the sentence separates them)

## 2. s140: clue vs default

- **Said:** "Remind me to ask my doctor about the tooth filling on Friday."
- **Expected:** resolve, target Dr. Subramanian
- **Why it's a good demo:** "tooth filling" is a clue for the dentist. (c) uses the stale default (family doctor).
- **clean** (`data/testset/audio/clean/s140.wav`), Pehchaan win:
  - heard: "Remind me to ask my doctor about the tooth filling on Friday."
  - (c): RESOLVE, action target = Dr. Venkataramana. "my doctor" -> Dr. Venkataramana (The user referred to 'my doctor', which matches the default for doctor in their context.)
  - Pehchaan: RESOLVE, action target = Dr. Subramanian. "my doctor" -> Dr. Subramanian (resolve: clue 'tooth' -> dentist; clue 'filling' -> dentist)
- **phone** (`data/testset/audio/phone/s140.wav`), Pehchaan win:
  - heard: "Remind me to ask my doctor about the tooth filling on Friday."
  - (c): RESOLVE, action target = Dr. Venkataramana. "my doctor" -> Dr. Venkataramana (The user referred to 'my doctor', which matches the default for doctor, Dr. Venkataramana.)
  - Pehchaan: RESOLVE, action target = Dr. Subramanian. "my doctor" -> Dr. Subramanian (resolve: clue 'tooth' -> dentist; clue 'filling' -> dentist)

## 3. s108: type mismatch

- **Said:** "Book a table at Venkataramana Restaurant for Sunday lunch."
- **Expected:** clarify
- **Why it's a good demo:** You can't book a table at a doctor. (c) maps it to a dental clinic; Pehchaan asks.
- **clean** (`data/testset/audio/clean/s108.wav`), Pehchaan win:
  - heard: "Book a table at Venkataramana restaurant for Sunday lunch."
  - (c): CORRECT, action target = Venkataramana Dental Care. "Venkataramana" -> Venkataramana Dental Care (Venkataramana refers to Venkataramana Dental Care, but in the context of booking a table, it is likely a misheard reference to a restaurant. However, there is no restaurant named Venkataramana in the context, so it remains unresolved.)
  - Pehchaan: ASKS: Dr. Venkataramana? "Venkataramana" -> kept (clarify: 'Venkataramana restaurant' sounds like a business, but Dr. Venkataramana is your family doctor: asking instead of guessing)
- **phone** (`data/testset/audio/phone/s108.wav`), Pehchaan win:
  - heard: "Book a table at Venkataramana restaurant for Sunday lunch."
  - (c): CORRECT, action target = Venkataramana Dental Care. "Venkataramana" -> Venkataramana Dental Care (Exact match for the restaurant name in the context.)
  - Pehchaan: ASKS: Dr. Venkataramana? "Venkataramana" -> kept (clarify: 'Venkataramana restaurant' sounds like a business, but Dr. Venkataramana is your family doctor: asking instead of guessing)

## 4. s067: misheard name

- **Said:** "Call Bhagyalakshmi Jewellers in Panjagutta and ask if the earrings are ready."
- **Expected:** correct, target Bhagyalakshmi Jewellers
- **Why it's a good demo:** "Padyalakshmi Jewelers" -> Bhagyalakshmi Jewellers by sound. (c) gives up and keeps it.
- **clean** (`data/testset/audio/clean/s067.wav`), Pehchaan win:
  - heard: "Call Padyalakshmi Jewelers in Punjabuta and ask if the earrings are ready."
  - (c): KEEP, no action target
  - Pehchaan: CORRECT, action target = Bhagyalakshmi Jewellers. "Padyalakshmi Jewelers" -> Bhagyalakshmi Jewellers (resolve: sounds like Bhagyalakshmi Jewellers (0.87), clear lead of 0.26); "Punjabuta" -> Panjagutta (resolve: sounds like Panjagutta (0.88), clear lead of 0.31)
- **phone** (`data/testset/audio/phone/s067.wav`), Pehchaan win:
  - heard: "Call Padyalakshmi Jewelers in Panjagutta and ask if the earrings are ready."
  - (c): KEEP, no action target
  - Pehchaan: CORRECT, action target = Bhagyalakshmi Jewellers. "Padyalakshmi Jewelers" -> Bhagyalakshmi Jewellers (resolve: sounds like Bhagyalakshmi Jewellers (0.87), clear lead of 0.26); "Panjagutta" -> Panjagutta (resolve: heard exactly 'Panjagutta')

## 5. s125: family word (reference)

- **Said:** "Bhaiya ko bolo Diwali pe ghar aa jaye."
- **Expected:** resolve, target Rajat Verma
- **Why it's a good demo:** "Bhaiya" in Hindi script is the user's elder brother Rajat. (c) picks a different contact.
- **clean** (`data/testset/audio/clean/s125.wav`), Pehchaan win:
  - heard: "भैया को बोलो, दिवाली पर घर आ जाएँ।"
  - (c): RESOLVE, action target = Aditya Rao. "भैया" -> Aditya Rao (The term 'Bhaiya' refers to the user's elder brother, who is identified as Aditya Rao in the context.)
  - Pehchaan: RESOLVE, action target = Rajat Verma. "भैया" -> Rajat Verma (resolve: family label: Bhaiya); "घर आ जाएँ।" -> kept (keep: 'घर आ जाएँ।' is unclear; best guess Nagarjuna Rao only 0.67)
- **phone** (`data/testset/audio/phone/s125.wav`), Pehchaan win:
  - heard: "भइया को बोलो दिवाली पर घर आ जाएँ।"
  - (c): RESOLVE, action target = Aditya Rao. "भइया" -> Aditya Rao (The term 'Bhaiya' refers to the user's elder brother, Aditya Rao, who is identified as such in the context.)
  - Pehchaan: RESOLVE, action target = Rajat Verma. "भइया" -> Rajat Verma (resolve: family label: Bhaiya); "घर आ जाएँ।" -> kept (keep: 'घर आ जाएँ।' is unclear; best guess Nagarjuna Rao only 0.67)

## Honest failure: s090: over-correction (Pehchaan's honest failure)

- **Said:** "Ee roju chala vedi ga undi, bayataki vellaku."
- **Expected:** keep
- **Why it's a good demo:** Telugu "ee roju" (= today) sounds like Dr. Raju at 0.80, just above the confidence bar, so Pehchaan "fixes" an ordinary word into a contact's name. (c) correctly leaves it alone. This is the most common kind of Pehchaan loss on the held-out set (over-correction 11/70 vs (c) 3/70).
- **clean** (`data/testset/audio/clean/s090.wav`), Pehchaan loss:
  - heard: "ఈ రోజు చాలా వేడిగా ఉంది. భయాతకి వెళ్ళకో."
  - (c): KEEP, no action target
  - Pehchaan: CORRECT, no action target. "రోజు" -> Dr. Raju (resolve: sounds like Dr. Raju (0.80), clear lead of 0.28)
- **phone** (`data/testset/audio/phone/s090.wav`), Pehchaan loss:
  - heard: "ఈ రోజు చాలా వేడిగా ఉంది. భయాతకి వెళ్ళకో."
  - (c): KEEP, no action target
  - Pehchaan: CORRECT, no action target. "రోజు" -> Dr. Raju (resolve: sounds like Dr. Raju (0.80), clear lead of 0.28)
