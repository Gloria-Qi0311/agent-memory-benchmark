"""Programmatic judge for fusion: word-boundary, case-insensitive match
of each ground-truth fact string against the agent's answer.

Returns recall in [0, 1]. Simple, no LLM, no bias.

Why word boundaries (not bare substring): short fact strings like "Go"
or "Zed" would otherwise match common English usage ("Go ahead", "rendering")
and inflate recall. We use `\\b<fact>\\b` so "Go" matches "Go" and "GO."
but not "Going" or "Government".
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
