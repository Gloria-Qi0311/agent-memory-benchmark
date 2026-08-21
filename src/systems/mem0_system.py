"""mem0 adapter.

Config choices (per docs/decisions.md, single-LLM constraint):
  - LLM: DeepSeek (reuses DEEPSEEK_API_KEY)
  - Embedder: sentence-transformers (huggingface provider), loaded from
    a locally-vendored model dir under repo/models/ — see docs/decisions.md
    for why we don't fetch at runtime.
  - Vector store: qdrant in embedded mode (no server, file-backed under a
    per-instance tempdir).
"""
import os
import shutil
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from .base import MemorySystem


load_dotenv()
# Benchmark runs do not need mem0's telemetry migration collection.  Leaving
# it enabled writes to a global ~/.mem0 directory, undermining hermetic runs
# and failing in restricted CI/workspace environments.
os.environ.setdefault("MEM0_TELEMETRY", "false")


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LOCAL_EMBED_MODEL = str(_REPO_ROOT / "models" / "multi-qa-MiniLM-L6-cos-v1")


def _build_config(persist_dir: str) -> dict:
    return {
        # mem0's extraction pipeline keeps the last messages in a separate
        # SQLite history database.  Its default lives in ~/.mem0/history.db,
        # which would leak conversation history between otherwise-isolated
        # benchmark cases that reuse the same user_id.  Keep that database in
        # the same per-adapter temp directory as Qdrant.
        "history_db_path": str(Path(persist_dir) / "history.db"),
        "llm": {
            "provider": "deepseek",
            "config": {
                "model": "deepseek-chat",
                "api_key": os.environ["DEEPSEEK_API_KEY"],
                "deepseek_base_url": os.environ.get(
                    "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
                ),
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": _LOCAL_EMBED_MODEL,
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "bench",
                "path": persist_dir,
                "embedding_model_dims": 384,
            },
        },
    }


class Mem0System(MemorySystem):
    name = "mem0"

    def __init__(self) -> None:
        from mem0 import Memory
        self._persist_dir = tempfile.mkdtemp(prefix="mem0_bench_")
        self._mem = Memory.from_config(_build_config(self._persist_dir))
        self._user = "bench-user"
        self._write_results: list[dict] = []

    def reset(self) -> None:
        # mem0 2.0+: filters dict instead of top-level user_id kwarg
        try: self._mem.delete_all(filters={"user_id": self._user})
        except Exception: pass

    def write(self, agent_id: str, text: str) -> None:
        result = self._mem.add(text, user_id=self._user, metadata={"agent_id": agent_id})
        self._write_results.append({
            "agent_id": agent_id,
            "text": text,
            "result": result,
        })

    def read(self, agent_id: str, query: str) -> str:
        results = self._mem.search(query, filters={"user_id": self._user})
        items = results.get("results", []) if isinstance(results, dict) else results
        return "\n".join(item.get("memory", "") for item in items)

    def debug_snapshot(self):
        results = self._mem.get_all(filters={"user_id": self._user})
        return results.get("results", []) if isinstance(results, dict) else results

    def debug_write_results(self):
        return list(self._write_results)

    def close(self) -> None:
        mem = getattr(self, "_mem", None)
        if mem is not None:
            vector_store = getattr(mem, "vector_store", None)
            client = getattr(vector_store, "client", None)
            close = getattr(client, "close", None)
            if callable(close):
                close()
            self._mem = None
        persist_dir = getattr(self, "_persist_dir", None)
        if persist_dir:
            shutil.rmtree(persist_dir, ignore_errors=True)
            self._persist_dir = None

    def __del__(self):
        try: self.close()
        except Exception: pass
