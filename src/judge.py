"""Programmatic judges. Token-boundary, case-insensitive substring match.

Task-specific score functions are added here as tasks are built. Shared
helper `_match` is the matching primitive everything builds on.

Why token boundaries (not bare substring): short fact strings like "Go"
would otherwise match "going". Python's ``\b`` is not suitable here because
it fails when a valid expected value ends in punctuation-like product-name
characters such as ``+`` (for example ``SSL 2+`` and ``Audioengine A2+``).
"""
import re


def _match(value: str, text_lower: str) -> bool:
    """Match an expected value without matching inside a larger word.

    A boundary means "not adjacent to a Unicode letter, digit, or
    underscore". The expected value itself is escaped literally, so names
    containing ``+``, ``.``, ``-`` or ``/`` remain valid. Callers currently
    pass lowercased text; casefolding again keeps this helper safe when used
    independently.
    """
    expected = value.strip().casefold()
    if not expected:
        return False
    pattern = r"(?<!\w)" + re.escape(expected) + r"(?!\w)"
    return re.search(pattern, text_lower.casefold()) is not None


def _t2_match(key: str, value: str, text: str) -> bool:
    """T2 exact match plus a small, authored accepted-answer set.

    Aliases are field-specific and deliberately narrow. For the question
    "Who is X traveling with?", answers such as "family" and "partner" are
    semantically identical to the dataset values "with family" and "with
    their partner". This avoids fuzzy or LLM judging while representing the
    ground truth correctly.
    """
    aliases = [value]
    if key == "travel_companion":
        aliases.extend({
            "with family": ["family"],
            "with their partner": ["partner", "their partner"],
            "with colleagues": ["colleagues"],
            "solo": ["alone"],
        }.get(value.casefold(), []))
    if key == "storage":
        # Dataset values use "4TB SSD" while concise natural answers may use
        # the equivalent "4TB of SSD storage" construction.
        storage = re.fullmatch(r"(\d+tb) ssd", value.casefold())
        if storage:
            aliases.append(f"{storage.group(1)} of ssd storage")
    return any(_match(alias, text) for alias in aliases)


# ---------------------------------------------------------------------------
# T2 — compound update scoring
# ---------------------------------------------------------------------------

def compound_update_score(probe_answers: list[dict], initial_facts: dict) -> dict:
    """Score a T2 case's probes.

    probe_answers: [{"key", "kind", "expected", "answer"}, ...]
      - kind is "updated" or "preserved"
      - for "updated" probes, expected is the NEW value (post-update)
      - for "preserved" probes, expected is the initial value
    initial_facts: full initial state (key -> initial value) — used for
      the confusion metric (did the answer for an updated key accidentally
      contain a DIFFERENT updated value?)

    Returns:
      update_recall:     fraction of "updated" probes where the new value
                         appeared in the answer
      no_confusion:      fraction of "updated" probes where the answer did
                         NOT accidentally contain the initial (old) value
                         for that key. If the answer contains BOTH old and
                         new, that's a partial confusion — counts as fail.
      no_collateral:     fraction of "preserved" probes where the initial
                         value still appeared (i.e. wasn't dropped)
      per_probe:         detailed hit/miss per probe for inspection
    """
    per_probe = []
    update_hits = 0
    update_total = 0
    no_confusion_hits = 0
    preserve_hits = 0
    preserve_total = 0

    for p in probe_answers:
        ans_lower = p["answer"].lower()
        expected_hit = _t2_match(p["key"], p["expected"], ans_lower)

        if p["kind"] == "updated":
            update_total += 1
            if expected_hit:
                update_hits += 1
            # confusion: did the answer surface the OLD (initial) value?
            old_val = initial_facts[p["key"]]
            old_value_present = _t2_match(p["key"], old_val, ans_lower)
            if not old_value_present:
                no_confusion_hits += 1
            per_probe.append({
                **p,
                "hit": expected_hit,
                "old_value_leaked": old_value_present,
            })
        else:  # preserved
            preserve_total += 1
            if expected_hit:
                preserve_hits += 1
            per_probe.append({
                **p,
                "hit": expected_hit,
            })

    return {
        "update_recall":     update_hits / update_total if update_total else 0.0,
        "no_confusion":      no_confusion_hits / update_total if update_total else 0.0,
        "no_collateral":     preserve_hits / preserve_total if preserve_total else 0.0,
        "update_hits":       update_hits,
        "update_total":      update_total,
        "preserve_hits":     preserve_hits,
        "preserve_total":    preserve_total,
        "per_probe":         per_probe,
    }


# ---------------------------------------------------------------------------
# T4 — split intake scoring
# ---------------------------------------------------------------------------

def split_intake_score_per_detail(probe_answers: list[dict]) -> dict:
    """Score per-detail probes.

    probe_answers: [{"key": str, "expected": str, "answer": str}, ...]
    A probe is a hit iff the expected value appears (word-boundary) in
    the answer to ITS OWN question — answers don't share information.

    Returns:
      - recall: hits / total
      - hits: list of keys that matched
      - misses: list of keys that did not
      - per_probe: detailed records for inspection
    """
    per_probe = []
    hits = []
    misses = []
    for p in probe_answers:
        hit = _match(p["expected"], p["answer"].lower())
        per_probe.append({
            "key": p["key"],
            "expected": p["expected"],
            "answer": p["answer"],
            "hit": hit,
        })
        (hits if hit else misses).append(p["key"])
    total = len(probe_answers)
    return {
        "recall": len(hits) / total if total else 0.0,
        "hits": hits,
        "misses": misses,
        "per_probe": per_probe,
    }


def split_intake_score_aggregate(answer: str, expected_by_key: dict) -> dict:
    """Score the single aggregate-probe answer.

    A key is a hit iff its expected value appears (word-boundary) anywhere
    in the single answer string.

    Returns same shape as the per-detail scorer for symmetry.
    """
    ans = answer.lower()
    per_probe = []
    hits = []
    misses = []
    for key, expected in expected_by_key.items():
        hit = _match(expected, ans)
        per_probe.append({
            "key": key,
            "expected": expected,
            "answer": answer,  # shared across keys in aggregate mode
            "hit": hit,
        })
        (hits if hit else misses).append(key)
    total = len(expected_by_key)
    return {
        "recall": len(hits) / total if total else 0.0,
        "hits": hits,
        "misses": misses,
        "per_probe": per_probe,
    }
