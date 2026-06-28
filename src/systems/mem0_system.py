"""mem0 adapter. Stub — fill in once mem0 SDK is installed and authenticated.

Spec: write() -> mem0.add(text, user_id=USER, agent_id=agent_id);
read() -> mem0.search(query, user_id=USER) and concatenate results.
"""
from .base import MemorySystem


class Mem0System(MemorySystem):
    name = "mem0"

    def __init__(self) -> None:
        from mem0 import Memory
        self._mem = Memory()
        self._user = "bench-user"

    def reset(self) -> None:
        try: self._mem.delete_all(user_id=self._user)
        except Exception: pass

    def write(self, agent_id: str, text: str) -> None:
        self._mem.add(text, user_id=self._user, metadata={"agent_id": agent_id})

    def read(self, agent_id: str, query: str) -> str:
        results = self._mem.search(query, user_id=self._user)
        items = results.get("results", []) if isinstance(results, dict) else results
        return "\n".join(item.get("memory", "") for item in items)
