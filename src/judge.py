"""Programmatic judges. Word-boundary, case-insensitive substring match.

Task-specific score functions are added here as tasks are built. Shared
helper `_match` is the matching primitive everything builds on.

Why word boundaries (not bare substring): short fact strings like "Go"
or "Zed" would otherwise match common English usage ("Go ahead",
"rendering") and inflate recall.
"""
import re


def _match(value: str, text_lower: str) -> bool:
    """Word-boundary, case-insensitive substring match. `text_lower` MUST be
    already lowercased by the caller — keeps callers honest about the cost
    of lowercasing inside hot loops."""
    pattern = r"\b" + re.escape(value.lower()) + r"\b"
    return re.search(pattern, text_lower) is not None


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
        expected_hit = _match(p["expected"], ans_lower)

        if p["kind"] == "updated":
            update_total += 1
            if expected_hit:
                update_hits += 1
            # confusion: did the answer surface the OLD (initial) value?
            old_val = initial_facts[p["key"]]
            old_value_present = _match(old_val, ans_lower)
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
