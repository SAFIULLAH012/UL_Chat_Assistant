"""
Thin wrapper around a local, persistent ChromaDB collection. Uses the
SAME loaded MiniLM model as the intent classifier (via model_loader) so
the ~400MB model is only loaded once per process.

Collection is created with cosine space explicitly, so query() returns
distances in [0, 2] (0 = identical direction). We convert that to a
0-1 "match_quality" score for easier thresholding elsewhere.
"""
import json
from functools import lru_cache

from .config import CHROMA_DB_PATH, CHROMA_COLLECTION, CHUNKS_FILE
from . import model_loader


class _SharedEmbeddingFunction:
    """Matches ChromaDB's EmbeddingFunction protocol: __call__(list[str]) -> list[list[float]]."""

    def __call__(self, input):  # noqa: A002 - name required by chromadb's protocol
        return model_loader.encode(list(input))

    def name(self):
        return "shared-minilm"


@lru_cache(maxsize=1)
def _client():
    import chromadb
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def _collection(create_if_missing=True):
    client = _client()
    ef = _SharedEmbeddingFunction()
    if create_if_missing:
        return client.get_or_create_collection(
            name=CHROMA_COLLECTION, embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return client.get_collection(name=CHROMA_COLLECTION, embedding_function=ef)


def rebuild_from_chunks(chunks):
    """chunks: list of dicts matching chatbot_chunks.json's shape. Wipes and recreates the collection."""
    client = _client()
    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass
    ef = _SharedEmbeddingFunction()
    coll = client.create_collection(
        name=CHROMA_COLLECTION, embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )
    ids = [c["id"] for c in chunks]
    docs = [c.get("search_text") or f"{c['title']} | {c['content']}" for c in chunks]
    metas = [{
        "type": c["type"], "category": c["category"], "title": c["title"],
        "content": c["content"], "verified": bool(c.get("verified", True)),
        "source": c.get("source", ""),
    } for c in chunks]
    coll.add(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def rebuild_from_file(path=None):
    chunks = json.loads((path or CHUNKS_FILE).read_text(encoding="utf-8"))
    return rebuild_from_chunks(chunks)


def query(text, n_results=3, where=None):
    """Returns a list of dicts: {id, title, content, type, category, verified, source, match_quality}."""
    coll = _collection(create_if_missing=False)
    res = coll.query(query_texts=[text], n_results=n_results, where=where)
    out = []
    ids = res.get("ids", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for i, meta, dist in zip(ids, metas, dists):
        match_quality = max(0.0, 1.0 - (dist / 2.0))
        out.append({
            "id": i, "title": meta.get("title"), "content": meta.get("content"),
            "type": meta.get("type"), "category": meta.get("category"),
            "verified": meta.get("verified", True), "source": meta.get("source", ""),
            "match_quality": round(match_quality, 4),
        })
    return out
