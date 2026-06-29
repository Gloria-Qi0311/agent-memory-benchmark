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
