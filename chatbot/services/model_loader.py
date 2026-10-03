"""
Loads the local MiniLM embedding model exactly once per process and hands
the same instance to both the intent classifier and the ChromaDB vector
store, so we don't keep two copies of a ~400MB model in memory.

First run needs internet (to download the model from Hugging Face once).
After that, sentence-transformers caches it under ~/.cache/torch/sentence_transformers/
and every further run is 100% offline.
"""
from functools import lru_cache

from .config import EMBEDDING_MODEL_NAME


@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def encode(texts, normalize=True):
    """texts: str or list[str] -> list[list[float]] (or single list[float] for a str input)."""
    model = get_embedder()
    single = isinstance(texts, str)
    out = model.encode(
        [texts] if single else list(texts),
        normalize_embeddings=normalize,
        show_progress_bar=False,
    )
    return out[0].tolist() if single else out.tolist()
