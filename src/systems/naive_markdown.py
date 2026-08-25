"""Simplest possible shared memory: all agents append to one in-memory list.
Read returns the whole thing. ~30 lines. Serves as the "naive baseline that
might surprisingly win" against the more complex memory systems."""
from .base import MemorySystem


class NaiveMarkdown(MemorySystem):
    name = "naive_markdown"

    def __init__(self) -> None:
        self._entries: list[str] = []

    def reset(self) -> None:
        self._entries = []

    def write(self, agent_id: str, text: str) -> None:
        self._entries.append(f"[{agent_id}] {text}")

    def read(self, agent_id: str, query: str) -> str:
        return "\n".join(self._entries)

    def debug_snapshot(self):
        return list(self._entries)
