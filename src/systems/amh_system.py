"""Agent Memory Hub adapter.

AMH is a Markdown + Git shared-memory system explicitly designed for
multi-agent workflows (Codex, Claude Code, MCP-aware agents share the
same memory root). Storage is filesystem, retrieval is keyword scoring
over Markdown entries — no vector store, no LLM extraction step.

This adapter is the only "explicitly multi-agent-native" system in the
current registry. Contrast with mem0/Letta (single-agent extraction+
vector systems being repurposed for multi-agent) and naive_markdown
(unstructured in-memory list).

Config choices:
  - One temp memory root per adapter instance (isolated between cases).
  - All writes go under scope="project", project=<persona-slug>, so a
    single case's writes group into one folder, matching the shape of
    "one user, many agents contributing to their shared memory."
  - read() uses AMH's search_entries with limit=10, concatenating the
    matched entries' content — same shape the mem0/pure_vector reads
    produce, so the runner treats all systems uniformly.
"""
import shutil
import tempfile
from pathlib import Path

from agent_memory_hub.store import (
    ensure_store,
    search_entries,
    write_memory,
)

from .base import MemorySystem


_PROJECT_SLUG = "bench"  # single project per instance — case reset wipes it


class AMHSystem(MemorySystem):
    name = "amh"

    def __init__(self) -> None:
        self._root: Path | None = None
        self._init_store()

    def _init_store(self) -> None:
        self._root = Path(tempfile.mkdtemp(prefix="amh_bench_"))
        ensure_store(self._root)

    def reset(self) -> None:
        # Wipe and re-init so each case starts from a clean memory folder.
        if self._root is not None:
            shutil.rmtree(self._root, ignore_errors=True)
        self._init_store()

    def write(self, agent_id: str, text: str) -> None:
        # We tag the source with agent_id so AMH's provenance is populated
        # even though the adapter doesn't do anything special with it.
        write_memory(
            self._root,
            content=text,
            kind="note",
            scope="project",
            project=_PROJECT_SLUG,
            source=agent_id,
        )

    def read(self, agent_id: str, query: str) -> str:
        scored = search_entries(
            self._root,
            query,
            project=_PROJECT_SLUG,
            limit=10,
        )
        return "\n".join(entry.content for _, entry in scored)

    def __del__(self):
        try:
            if self._root is not None:
                shutil.rmtree(self._root, ignore_errors=True)
        except Exception:
            pass
