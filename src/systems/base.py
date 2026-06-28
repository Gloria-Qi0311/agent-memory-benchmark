"""Abstract interface every memory system must implement.

Kept deliberately minimal: write a piece of text tagged with an agent_id,
and read whatever the system considers relevant for a query. Each system is
free to use any internal representation (markdown, vector store, graph...).
"""
from abc import ABC, abstractmethod


class MemorySystem(ABC):
    name: str = "unnamed"

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def write(self, agent_id: str, text: str) -> None: ...

    @abstractmethod
    def read(self, agent_id: str, query: str) -> str: ...
