"""Regex-based update-aware markdown.

Like naive_markdown, but on every write it inspects the text for an
explicit retirement pattern ("don't use X anymore" / "switched to Y...
don't use X anymore"). When matched, prior entries that mention X (the
retired value) are physically removed before the new entry is appended.

The point of this system is to ask: does processing the explicit-update
phrasing need an LLM at all, or is a 20-line regex enough? It is
deliberately the dumbest possible implementation of update reconciliation.

Retirement patterns we match (case-insensitive):
  - "doesn't use X anymore"
  - "don't use X anymore"
  - "no longer uses X"
  - "switched to Y as their <cat>. They don't use X anymore." (our case fmt)

If the same write also mentions a replacement (e.g. "switched to Y"),
we keep the new utterance verbatim — the read step will still expose Y.
"""
import re
from .base import MemorySystem


# Identify retired value via several common explicit phrasings.
_RETIRE_PATTERNS = [
    re.compile(r"(?:doesn't|don't|does not|do not)\s+use\s+([A-Za-z][\w.+\- ]*?)\s+(?:anymore|any more|any longer)", re.IGNORECASE),
    re.compile(r"no longer use[ds]?\s+([A-Za-z][\w.+\- ]*?)(?:[.,;]|$)", re.IGNORECASE),
]


def _extract_retired_values(text: str) -> list[str]:
    """Return the list of values the speaker explicitly retires in this text."""
    out: list[str] = []
    for pat in _RETIRE_PATTERNS:
        for m in pat.finditer(text):
            # Strip trailing whitespace and any single trailing period the regex
            # may have grabbed inside the value group.
            v = m.group(1).strip().rstrip(".")
            if v:
                out.append(v)
    return out


def _mentions(entry: str, value: str) -> bool:
    """Word-boundary match — same convention as the judge."""
    return re.search(r"\b" + re.escape(value.lower()) + r"\b", entry.lower()) is not None


class RegexMarkdown(MemorySystem):
    name = "regex_markdown"

    def __init__(self) -> None:
        self._entries: list[str] = []

    def reset(self) -> None:
        self._entries = []

    def write(self, agent_id: str, text: str) -> None:
        retired = _extract_retired_values(text)
        if retired:
            # Drop any earlier entry that mentions a retired value, UNLESS that
            # entry is the new utterance itself (it can mention X to say X is
            # retired). We rebuild the list without the offending entries.
            keep = []
            for e in self._entries:
                if any(_mentions(e, v) for v in retired):
                    continue
                keep.append(e)
            self._entries = keep
        self._entries.append(f"[{agent_id}] {text}")

    def read(self, agent_id: str, query: str) -> str:
        return "\n".join(self._entries)
