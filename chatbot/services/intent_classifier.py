"""
Offline intent classifier: no training step, just k-nearest-neighbours
over MiniLM embeddings of the labelled examples in intents.json.

Why kNN instead of one centroid per intent: some intents (e.g.
"office_info") cover deliberately varied phrasings, so a single average
vector blurs them together. Comparing against every individual example
and voting keeps each phrasing's signal intact.

Example embeddings are cached to disk next to intents.json
(intents_cache.json) keyed by a hash of the file content, so re-running
after editing intents.json rebuilds automatically, but normal runs
don't re-embed ~110 short strings every process start.
"""
import hashlib
import json
from collections import Counter
from functools import lru_cache

import numpy as np

from .config import INTENTS_FILE, INTENT_TOP_K
from . import model_loader

_CACHE_FILE = INTENTS_FILE.parent / "intents_cache.json"


def _file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _load_intents_raw():
    return json.loads(INTENTS_FILE.read_text(encoding="utf-8"))["intents"]


@lru_cache(maxsize=1)
def _load_index():
    """Returns (examples: list[str], labels: list[str], routes: dict[intent->route], vectors: np.ndarray)."""
    intents = _load_intents_raw()
    routes = {i["intent"]: i["route"] for i in intents}

    examples, labels = [], []
    for i in intents:
        for ex in i["examples"]:
            examples.append(ex)
            labels.append(i["intent"])

    h = _file_hash(INTENTS_FILE)
    if _CACHE_FILE.exists():
        cached = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        if cached.get("hash") == h and cached.get("examples") == examples:
            return examples, labels, routes, np.array(cached["vectors"], dtype="float32")

    vectors = np.array(model_loader.encode(examples), dtype="float32")
    _CACHE_FILE.write_text(json.dumps({
        "hash": h, "examples": examples, "vectors": vectors.tolist(),
    }, ensure_ascii=False), encoding="utf-8")
    return examples, labels, routes, vectors


def warm_cache():
    """Call once at server startup (or from the build_chatbot_index command) to pay the embedding cost up front."""
    _load_index()


def classify(query_normalized: str):
    """Returns dict: {intent, confidence, route, top_matches: [(example, label, sim), ...]}."""
    examples, labels, routes, vectors = _load_index()
    if not query_normalized:
        return {"intent": "greeting_smalltalk", "confidence": 0.0, "route": routes.get("greeting_smalltalk", "canned"), "top_matches": []}

    qvec = np.array(model_loader.encode(query_normalized), dtype="float32")
    sims = vectors @ qvec  # vectors are normalized, qvec is normalized -> dot product = cosine similarity

    k = min(INTENT_TOP_K, len(sims))
    top_idx = np.argsort(-sims)[:k]

    votes = Counter()
    score_sum = Counter()
    for idx in top_idx:
        lbl = labels[idx]
        votes[lbl] += 1
        score_sum[lbl] += float(sims[idx])

    winner = max(votes.items(), key=lambda kv: (kv[1], score_sum[kv[0]]))[0]
    confidence = score_sum[winner] / votes[winner]

    return {
        "intent": winner,
        "confidence": round(confidence, 4),
        "route": routes.get(winner, "chroma"),
        "top_matches": [(examples[i], labels[i], round(float(sims[i]), 4)) for i in top_idx],
    }
