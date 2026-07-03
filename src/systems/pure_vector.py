"""Pure vector-store memory (no LLM extraction).

Writes the raw user statement directly into a vector store. Reads
retrieve top-k by cosine similarity and return them concatenated.

This system is designed as a controlled contrast to `mem0`:
  - mem0 pipeline:         extraction (LLM) -> vector store -> retrieval
  - pure_vector pipeline:                                     vector store -> retrieval

If pure_vector recall > mem0 recall on the same task, the LLM extraction
step is the drag. If pure_vector recall ≈ mem0 recall, vector retrieval
is the primary loss. Either result is informative.

Design choices:
  - Embedder: sentence-transformers/multi-qa-MiniLM-L6-cos-v1
    (same model mem0 uses in this repo, for apples-to-apples comparison).
  - Store: in-process numpy — one persona per case, at most a few dozen
    writes, so a full-dot-product scan is trivially fast. Avoids the
    qdrant tempdir + concurrent-instance headaches.
  - Read: return top-K entries. K is set to 8 (large enough that a single
    dense statement isn't clipped, small enough that unrelated cases
    don't bleed in).
"""
from pathlib import Path

from .base import MemorySystem


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LOCAL_EMBED_MODEL = str(_REPO_ROOT / "models" / "multi-qa-MiniLM-L6-cos-v1")
_TOP_K = 8


class PureVector(MemorySystem):
    name = "pure_vector"

    def __init__(self) -> None:
        # Lazy import so importing the package doesn't force the model load.
        from sentence_transformers import SentenceTransformer
        import numpy as np
        self._np = np
        self._model = SentenceTransformer(_LOCAL_EMBED_MODEL)
        self._entries: list[str] = []
        self._vectors: list = []  # list of np.ndarray, one per entry

    def reset(self) -> None:
        self._entries = []
        self._vectors = []

    def _embed(self, text: str):
        vec = self._model.encode(text, normalize_embeddings=True)
        return self._np.asarray(vec, dtype="float32")

    def write(self, agent_id: str, text: str) -> None:
        # agent_id ignored — pure_vector doesn't model provenance
        self._entries.append(text)
        self._vectors.append(self._embed(text))

    def read(self, agent_id: str, query: str) -> str:
        if not self._entries:
            return ""
        q = self._embed(query)
        # cosine similarity == dot product on already-normalized vectors
        mat = self._np.stack(self._vectors)
        sims = mat @ q
        order = self._np.argsort(-sims)[:_TOP_K]
        return "\n".join(self._entries[int(i)] for i in order)
