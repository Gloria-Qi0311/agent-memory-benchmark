from .base import MemorySystem


class NoMemory(MemorySystem):
    name = "no_memory"

    def reset(self) -> None: pass
    def write(self, agent_id: str, text: str) -> None: pass
    def read(self, agent_id: str, query: str) -> str: return ""
