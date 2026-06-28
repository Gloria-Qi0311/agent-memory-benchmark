"""mem0 adapter.

Config choices (per docs/decisions.md, single-LLM constraint):
  - LLM: DeepSeek (reuses DEEPSEEK_API_KEY)
  - Embedder: fastembed (local ONNX model, no extra API key)
  - Vector store: qdrant in embedded mode (no server, file-backed)

The embedder downloads ~150MB on first run to ~/.cache/. Subsequent runs are fast.
"""
import os
import shutil
import tempfile
from pathlib import Path
from .base import MemorySystem


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# Pre-downloaded sentence-transformers model (HuggingFace HEAD requests
# fail under this machine's Python 3.9 + LibreSSL stack, so we ship the
# model files locally and point at the directory).
_LOCAL_EMBED_MODEL = str(_REPO_ROOT / "models" / "multi-qa-MiniLM-L6-cos-v1")


def _build_config(persist_dir: str) -> dict:
    return {
        "llm": {
            "provider": "deepseek",
            "config": {
                "model": "deepseek-chat",
                "api_key": os.environ["DEEPSEEK_API_KEY"],
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
        self._Memory = Memory
        self._persist_dir = tempfile.mkdtemp(prefix="mem0_bench_")
        self._mem = Memory.from_config(_build_config(self._persist_dir))
        self._user = "bench-user"

    def reset(self) -> None:
        # mem0 2.0+: filters dict instead of top-level user_id kwarg
        try: self._mem.delete_all(filters={"user_id": self._user})
        except Exception: pass

    def write(self, agent_id: str, text: str) -> None:
        self._mem.add(text, user_id=self._user, metadata={"agent_id": agent_id})

    def read(self, agent_id: str, query: str) -> str:
        results = self._mem.search(query, filters={"user_id": self._user})
        items = results.get("results", []) if isinstance(results, dict) else results
        return "\n".join(item.get("memory", "") for item in items)

    def __del__(self):
        try: shutil.rmtree(self._persist_dir, ignore_errors=True)
        except Exception: pass
