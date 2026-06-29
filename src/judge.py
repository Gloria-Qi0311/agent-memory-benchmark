"""Programmatic judges. Word-boundary, case-insensitive substring match.

Why word boundaries (not bare substring): short fact strings like "Go"
or "Zed" would otherwise match common English usage ("Go ahead", "rendering")
and inflate recall.
"""
import re


def _match(fact: str, answer_lower: str) -> bool:
    pattern = r"\b" + re.escape(fact.lower()) + r"\b"
    return re.search(pattern, answer_lower) is not None


def fusion_score(answer: str, ground_truth_facts: list[str]) -> dict:
    ans = answer.lower()
    hits = [f for f in ground_truth_facts if _match(f, ans)]
    misses = [f for f in ground_truth_facts if not _match(f, ans)]
    return {
        "recall": len(hits) / len(ground_truth_facts) if ground_truth_facts else 0.0,
        "hits": hits,
        "misses": misses,
    }


def rewrite_score_per_fact(probe_answers: list[dict]) -> dict:
    """Score a per-fact rewrite case.

    probe_answers: list of {"category": ..., "expected": ..., "kind": "updated"|"preserved", "answer": ...}

    Returns:
      - update_correct: 0 or 1 (whether the single 'updated' probe matched)
      - preservation_rate: hits / (#preserved)
      - per_probe: detailed list for inspection
    """
    per_probe = []
    update_correct: int | None = None
    preserved_hits = 0
    preserved_total = 0

    for p in probe_answers:
        hit = _match(p["expected"], p["answer"].lower())
        per_probe.append({
            "category": p["category"],
            "expected": p["expected"],
            "kind": p["kind"],
            "answer": p["answer"],
            "hit": hit,
        })
        if p["kind"] == "updated":
            update_correct = 1 if hit else 0
        elif p["kind"] == "preserved":
            preserved_total += 1
            if hit:
                preserved_hits += 1

    if update_correct is None:
        raise ValueError("rewrite case had no 'updated' probe")

    return {
        "update_correct": update_correct,
        "preservation_rate": preserved_hits / preserved_total if preserved_total else 0.0,
        "preserved_hits": preserved_hits,
        "preserved_total": preserved_total,
        "per_probe": per_probe,
    }


def rewrite_score_aggregate(answer: str, expected_by_category: dict[str, str], update_category: str) -> dict:
    """Score an aggregate rewrite case (one question asks for everything).

    expected_by_category: {category -> expected_value_after_update}
    update_category: the category that was updated

    Returns same shape as rewrite_score_per_fact for symmetry.
    """
    ans = answer.lower()
    per_probe = []
    update_correct: int | None = None
    preserved_hits = 0
    preserved_total = 0

    for cat, expected in expected_by_category.items():
        hit = _match(expected, ans)
        kind = "updated" if cat == update_category else "preserved"
        per_probe.append({
            "category": cat,
            "expected": expected,
            "kind": kind,
            "answer": answer,  # all probes share the same answer in aggregate mode
            "hit": hit,
        })
        if kind == "updated":
            update_correct = 1 if hit else 0
        else:
            preserved_total += 1
            if hit:
                preserved_hits += 1

    if update_correct is None:
        raise ValueError("aggregate rewrite case had no update_category match")

    return {
        "update_correct": update_correct,
        "preservation_rate": preserved_hits / preserved_total if preserved_total else 0.0,
        "preserved_hits": preserved_hits,
        "preserved_total": preserved_total,
        "per_probe": per_probe,
    }
