"""Long-context baseline.

Stores every write verbatim, returns them all (no agent tags) on read.
This isolates the contribution of agent attribution in `naive_markdown`:
if `long_context` performs the same, the attribution doesn't help; if
worse, it does.

Like `naive_markdown`, this assumes the model's context window is large
enough to fit every utterance. For our DeepSeek setup (64k tokens) and
case shapes (a few dozen short sentences), this is comfortably true.
"""
from .base import MemorySystem


class LongContext(MemorySystem):
    name = "long_context"

    def __init__(self) -> None:
        self._entries: list[str] = []

    def reset(self) -> None:
        self._entries = []

    def write(self, agent_id: str, text: str) -> None:
        # Deliberately ignore agent_id — that's the whole point of comparing
        # against naive_markdown.
        self._entries.append(text)

    def read(self, agent_id: str, query: str) -> str:
        return "\n".join(self._entries)
