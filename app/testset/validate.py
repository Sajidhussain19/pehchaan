"""
app/testset/validate.py — loads the test set and checks it against the knowledge base.

WHAT: `load_testset()` reads data/testset/sentences.json into `Sentence` models.
      `validate_testset()` runs rules that need the KB or the whole set:
        - sentence ids are unique
        - every entity_id / caller_contact_id / candidate_id / action target exists in the KB,
          and has the right type
        - each category's rules hold (e.g. control sentences have no entities,
          out_of_kb names really are NOT in the KB)
        - both the dev and test splits contain every category
      Run it directly for a short summary:  python -m app.testset.validate
WHY:  If the answer key is wrong, every reported number is wrong. These checks make the
      ground truth trustworthy before we spend money transcribing audio against it.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from app.config import PROJECT_ROOT
from app.kb.loader import _normalise, all_surface_forms, get_by_id, get_primary_for
from app.testset.models import RealSpeechClip, Sentence

TESTSET_PATH = PROJECT_ROOT / "data" / "testset" / "sentences.json"

# Planned size of each category (min, max). Grew in Module 8's Step 0 (21 hard dev-only sentences).
EXPECTED_SIZES = {
    "in_kb": (75, 85),
    "out_of_kb": (10, 15),
    "control": (10, 15),
    "ambiguous": (12, 16),
    "context_mismatch": (8, 12),
    "reference": (19, 25),
    "unfamiliar_near_match": (5, 8),
    "stale_default": (5, 8),
}

# Real speakers (AI4Bharat Svarah sample), fetched by scripts/fetch_real_speech.py.
REALSPEECH_DIR = PROJECT_ROOT / "data" / "realspeech"
REALSPEECH_MANIFEST = REALSPEECH_DIR / "manifest.json"


class TestsetValidationError(ValueError):
    """Raised when the test set breaks one of our rules."""

    __test__ = False  # tell pytest this is not a test class, despite the name


def load_testset(path: Path = TESTSET_PATH) -> list[Sentence]:
    """Read and validate (one sentence at a time) every test sentence."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    return [Sentence.model_validate(row) for row in rows]


def _check_id(problems: list[str], sid: str, what: str, entity_id: str, expected_type: str | None = None):
    """Helper: record a problem if a KB id does not exist or has the wrong type."""
    entity = get_by_id(entity_id)
    if entity is None:
        problems.append(f"{sid}: {what} {entity_id!r} is not in the KB")
    elif expected_type and entity.type != expected_type:
        problems.append(f"{sid}: {what} {entity_id!r} is a {entity.type}, expected {expected_type}")


def _check_reference_sentence(problems: list[str], s: Sentence, linked: list) -> None:
    """Rules for the "reference" category ("my doctor", "Amma", "the usual pharmacy").

    The ground truth must agree with the KB: if we say "primary", that person really is a
    default for some role; "family_label" really is their family word; "usual" really is
    a usual business. Otherwise the answer key would quietly disagree with the data.
    """
    if s.expected_behaviour not in ("resolve", "clarify"):
        problems.append(f"{s.id}: reference needs behaviour 'resolve' or 'clarify'")
    if not s.references:
        problems.append(f"{s.id}: reference sentence needs at least one reference")
    # Names that appear alongside the reference ("…in Kukatpally") must be linked to the KB.
    if len(linked) != len(s.entities):
        problems.append(f"{s.id}: named entities in a reference sentence must be linked to the KB")

    ambiguous = [r for r in s.references if r.resolution_reason == "ambiguous"]
    if s.expected_behaviour == "clarify" and (not ambiguous or len(s.candidate_ids) < 2):
        problems.append(f"{s.id}: reference clarify needs an ambiguous reference and 2+ candidates")
    if s.expected_behaviour == "resolve" and ambiguous:
        problems.append(f"{s.id}: a resolved reference sentence cannot contain an ambiguous reference")

    for ref in s.references:
        if ref.resolved_entity_id is None:
            continue
        _check_id(problems, s.id, "resolved_entity_id", ref.resolved_entity_id)
        entity = get_by_id(ref.resolved_entity_id)
        if entity is None:
            continue
        ctx = entity.context
        if ref.resolution_reason == "primary" and not ctx.get("is_primary_for"):
            problems.append(f"{s.id}: {entity.name} is not a default for any role (reason 'primary')")
        if ref.resolution_reason == "family_label":
            label = ctx.get("family_label")
            if not label or _normalise(label) not in _normalise(ref.surface):
                problems.append(f"{s.id}: {ref.surface!r} does not use {entity.name}'s family label")
        if ref.resolution_reason == "usual" and not ctx.get("is_usual"):
            problems.append(f"{s.id}: {entity.name} is not a usual business (reason 'usual')")

    # The action must point at someone the sentence actually refers to.
    target = s.expected_action.target_entity_id
    allowed = {r.resolved_entity_id for r in s.references} | {span.entity_id for span in linked}
    if target is not None and target not in allowed:
        problems.append(f"{s.id}: action target {target} is not among the resolved references or entities")


def _check_stale_default(problems: list[str], s: Sentence) -> None:
    """A stale-default line: the user HAS a default for the role, but a clue points elsewhere.

    Example: "Call my doctor about my eye drops". The default doctor is Dr. Venkataramana,
    but "eye drops" means the eye specialist, Dr. Raju. We check that, for each resolved person:
      - the reason is "clue" (the clue must win), and
      - they are NOT the default, while someone ELSE is the default for one of their roles.
    If no competing default existed, the line would not test anything "stale".
    """
    if s.expected_behaviour != "resolve":
        problems.append(f"{s.id}: stale_default needs behaviour 'resolve'")
    for ref in s.references:
        entity = get_by_id(ref.resolved_entity_id) if ref.resolved_entity_id else None
        if ref.resolution_reason != "clue" or entity is None:
            problems.append(f"{s.id}: stale_default references must be resolved by a 'clue'")
            continue
        others_default = [
            role for role in entity.context.get("roles", [])
            if (default := get_primary_for(role)) is not None and default.id != entity.id
        ]
        if not others_default:
            problems.append(f"{s.id}: {entity.name} has no competing default, so this is not a stale-default case")


def _check_unfamiliar_near_match(problems: list[str], s: Sentence, linked: list, kb_forms: dict) -> None:
    """A name ONE sound away from a contact, but not a contact ("Rohan" vs contact "Rohit").

    Expected: keep it (it's probably someone else), or clarify with the nearby contact.
    Never silently resolve. So: nothing linked, the name is truly absent from the KB,
    clarify is listed as acceptable, and the nearby contacts are given as candidates.
    """
    if s.expected_behaviour != "keep" or "clarify" not in s.also_acceptable:
        problems.append(f"{s.id}: unfamiliar_near_match expects 'keep' with 'clarify' also acceptable")
    if not s.entities or linked:
        problems.append(f"{s.id}: unfamiliar_near_match names must not be linked to the KB")
    for span in s.entities:
        if _normalise(span.surface) in kb_forms:
            problems.append(f"{s.id}: near-match name {span.surface!r} IS in the KB")
    if not s.candidate_ids:
        problems.append(f"{s.id}: list the nearby contact(s) in candidate_ids")
    if s.expected_action.target_entity_id is not None:
        problems.append(f"{s.id}: an unfamiliar name must not have a KB action target")


def validate_testset(sentences: list[Sentence]) -> None:
    """Whole-set checks. Collects every problem and raises them together."""
    problems: list[str] = []
    kb_forms = all_surface_forms()  # every KB name and alias, lower-cased

    # 1. Unique sentence ids.
    counts = Counter(s.id for s in sentences)
    problems += [f"duplicate sentence id {sid}" for sid, n in counts.items() if n > 1]

    for s in sentences:
        # 2. Every KB reference must exist (and be the right type).
        for span in s.entities:
            if span.entity_id is not None:
                _check_id(problems, s.id, "entity_id", span.entity_id, span.type)
        if s.caller_contact_id is not None:
            _check_id(problems, s.id, "caller_contact_id", s.caller_contact_id, "person")
        for cid in s.candidate_ids:
            _check_id(problems, s.id, "candidate_id", cid)
        if s.expected_action.target_entity_id is not None:
            _check_id(problems, s.id, "action target", s.expected_action.target_entity_id)

        linked = [span for span in s.entities if span.entity_id is not None]

        # 3. Category rules: each category tests one specific behaviour.
        if s.category == "in_kb":
            if s.expected_behaviour != "correct" or not s.entities or len(linked) != len(s.entities):
                problems.append(f"{s.id}: in_kb needs behaviour 'correct' and every entity linked to the KB")
            # The script we read aloud uses the CORRECT spelling, so the ground truth is
            # exactly the canonical name. Speech-to-text then has to get it right (or we fix it).
            for span in linked:
                entity = get_by_id(span.entity_id)
                if entity is not None and span.surface != entity.name:
                    problems.append(f"{s.id}: in_kb surface {span.surface!r} is not the canonical name {entity.name!r}")
        elif s.category == "out_of_kb":
            if s.expected_behaviour != "keep" or not s.entities or linked:
                problems.append(f"{s.id}: out_of_kb needs behaviour 'keep' and only unlinked entities")
            # The whole point: these names must truly be absent from the KB.
            for span in s.entities:
                if _normalise(span.surface) in kb_forms:
                    problems.append(f"{s.id}: out_of_kb name {span.surface!r} IS in the KB")
        elif s.category == "control":
            if s.expected_behaviour != "keep" or s.entities:
                problems.append(f"{s.id}: control needs behaviour 'keep' and no entities")
        elif s.category == "ambiguous":
            if s.expected_behaviour not in ("resolve", "clarify"):
                problems.append(f"{s.id}: ambiguous needs behaviour 'resolve' or 'clarify'")
            if s.expected_behaviour == "clarify" and len(s.candidate_ids) < 2:
                problems.append(f"{s.id}: ambiguous clarify needs both near-identical candidates")
        elif s.category == "context_mismatch":
            if s.expected_behaviour not in ("clarify", "keep") or linked:
                problems.append(f"{s.id}: context_mismatch needs 'clarify' or 'keep' and no linked entities")
        elif s.category == "reference":
            _check_reference_sentence(problems, s, linked)
        elif s.category == "stale_default":
            _check_reference_sentence(problems, s, linked)
            _check_stale_default(problems, s)
        elif s.category == "unfamiliar_near_match":
            _check_unfamiliar_near_match(problems, s, linked, kb_forms)

        # Personal references belong only to the reference-style categories.
        if s.references and s.category not in ("reference", "stale_default"):
            problems.append(f"{s.id}: only 'reference' / 'stale_default' sentences may have references")

        # 4. In the ambiguous category, "resolve" must name exactly one KB entity,
        #    and the action must point at it.
        if s.category == "ambiguous" and s.expected_behaviour == "resolve":
            if len(linked) != 1:
                problems.append(f"{s.id}: resolve needs exactly one linked entity")
            elif s.expected_action.target_entity_id not in (None, linked[0].entity_id):
                problems.append(f"{s.id}: resolve action target differs from the resolved entity")

    # 5. Sizes stay close to the plan, so no category quietly shrinks when the file is edited.
    #    Only checked for the real file (a handful of sentences in a unit test is fine).
    if len(sentences) >= 50:
        for cat, (low, high) in EXPECTED_SIZES.items():
            n = sum(s.category == cat for s in sentences)
            if not low <= n <= high:
                problems.append(f"category {cat!r} has {n} sentences, expected {low}-{high}")
        n_dev = sum(s.split == "dev" for s in sentences)
        if not 60 <= n_dev <= 70:
            problems.append(f"dev split has {n_dev} sentences, expected 60-70")

    # 6. Stratified split: dev and test must each contain every category,
    #    otherwise tuning on dev would never see some kinds of sentence.
    categories = {s.category for s in sentences}
    for split in ("dev", "test"):
        missing = categories - {s.category for s in sentences if s.split == split}
        if missing:
            problems.append(f"split {split!r} is missing categories: {sorted(missing)}")

    if problems:
        raise TestsetValidationError("Test set is invalid:\n  - " + "\n  - ".join(problems))


def load_realspeech(path: Path = REALSPEECH_MANIFEST) -> list[RealSpeechClip]:
    """Read the real-speech manifest. Returns [] if the sample has not been fetched yet."""
    if not path.exists():
        return []
    return [RealSpeechClip.model_validate(row) for row in json.loads(path.read_text(encoding="utf-8"))]


def validate_realspeech(clips: list[RealSpeechClip], root: Path = PROJECT_ROOT) -> None:
    """Checks for the real-speech sample: unique ids, audio files exist, several different speakers.

    The audio is NOT in git (it is re-downloaded from Hugging Face by scripts/fetch_real_speech.py, under the
    dataset's own terms). So "no audio at all" just means "not fetched yet" and is fine: the manifest,
    the saved transcripts and the results still work. SOME files missing means a broken download: an error.
    """
    problems: list[str] = []
    counts = Counter(c.id for c in clips)
    problems += [f"duplicate real-speech id {cid}" for cid, n in counts.items() if n > 1]
    present = [c for c in clips if (root / c.audio_path).exists()]
    if present:  # audio was fetched: then every file must be there
        for c in clips:
            if not (root / c.audio_path).exists():
                problems.append(f"{c.id}: audio file missing: {c.audio_path}")
    # The point is to test REAL variety; one speaker would just test one voice.
    if clips and len({c.speaker_id for c in clips}) < min(5, len(clips)):
        problems.append("real-speech sample should come from at least 5 different speakers")
    if problems:
        raise TestsetValidationError("Real-speech sample is invalid:\n  - " + "\n  - ".join(problems))


def main() -> int:
    """Load, validate and print a short summary table."""
    try:
        sentences = load_testset()
        validate_testset(sentences)
        real = load_realspeech()
        validate_realspeech(real)
    except (TestsetValidationError, ValueError) as err:
        print(f"[ERROR] {err}")
        return 1

    print(f"Pehchaan test set: {len(sentences)} sentences\n")
    print(f"  {'category':<24}{'dev':>5}{'test':>6}{'total':>7}")
    for cat in EXPECTED_SIZES:
        dev = sum(s.category == cat and s.split == "dev" for s in sentences)
        test = sum(s.category == cat and s.split == "test" for s in sentences)
        print(f"  {cat:<24}{dev:>5}{test:>6}{dev + test:>7}")
    dev_total = sum(s.split == "dev" for s in sentences)
    print(f"  {'TOTAL':<24}{dev_total:>5}{len(sentences) - dev_total:>6}{len(sentences):>7}")

    print("\nBy expected behaviour:", dict(Counter(s.expected_behaviour for s in sentences)))
    print("By direction:", dict(Counter(s.direction for s in sentences)))
    print("Entity mentions:", sum(len(s.entities) for s in sentences))
    if real:
        print(f"\nReal speech: {len(real)} clips from {len({c.speaker_id for c in real})} speakers")
    else:
        print("\nReal speech: not fetched yet (python scripts/fetch_real_speech.py)")
    print("\n[OK] Test set loaded and validated against the knowledge base.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
