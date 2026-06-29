"""Programmatic judges. Word-boundary, case-insensitive substring match.

Task-specific score functions are added here as tasks are built. Shared
helper `_match` is the matching primitive everything builds on.

Why word boundaries (not bare substring): short fact strings like "Go"
or "Zed" would otherwise match common English usage ("Go ahead",
"rendering") and inflate recall.

v0 fusion + rewrite scorers were removed when v1 superseded those tasks.
T4 (split intake) and later v1 tasks add their scorers here.
"""
import re


def _match(value: str, text_lower: str) -> bool:
    """Word-boundary, case-insensitive substring match. `text_lower` MUST be
    already lowercased by the caller — keeps callers honest about the cost
    of lowercasing inside hot loops."""
    pattern = r"\b" + re.escape(value.lower()) + r"\b"
    return re.search(pattern, text_lower) is not None
