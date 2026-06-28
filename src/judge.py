"""Programmatic judge for fusion: count how many ground-truth fact strings
appear in the agent's answer (case-insensitive substring match).

Returns recall in [0, 1]. Simple, no LLM, no bias.
"""


def fusion_score(answer: str, ground_truth_facts: list[str]) -> dict:
    ans = answer.lower()
    hits = [f for f in ground_truth_facts if f.lower() in ans]
    return {
        "recall": len(hits) / len(ground_truth_facts) if ground_truth_facts else 0.0,
        "hits": hits,
        "misses": [f for f in ground_truth_facts if f.lower() not in ans],
    }
