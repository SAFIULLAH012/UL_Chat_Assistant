"""
Shared settings for the offline chatbot pipeline.

All thresholds here are STARTING POINTS. They were not calibrated
against the real embedding model (this was built without internet
access to download it), so the first thing to do after setup is the
calibration step described in the README — run chat_cli.py with ~30
real student-style questions and adjust these two numbers until the
"I don't know" fallback triggers only when it should.
"""
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"

ALIASES_FILE = DATA_DIR / "aliases.json"
INTENTS_FILE = DATA_DIR / "intents.json"
CHUNKS_FILE = DATA_DIR / "chatbot_chunks.json"

CHROMA_DB_PATH = str(APP_DIR / "chroma_db")
CHROMA_COLLECTION = "university_layyah"

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Intent classification: minimum average cosine similarity (0-1) of the
# winning intent's nearest examples. Below this, we still use the intent
# for entity-routing hints but fall back to a generic search rather than
# trusting a specific SQL route (e.g. bus_schedule).
INTENT_CONFIDENCE_THRESHOLD = 0.45
INTENT_TOP_K = 5

# Retrieval: ChromaDB collection is created with cosine space, so distance
# is in [0, 2] (0 = identical). match_quality = 1 - distance/2, in [0, 1].
# Below this match_quality, don't answer from that chunk - say "not sure".
RETRIEVAL_CONFIDENCE_THRESHOLD = 0.55
RETRIEVAL_TOP_N = 5

FALLBACK_REPLY = (
    "Mujhe is sawal ka pakka jawab nahi mil saka. Barah-e-meherbani Admission/Info "
    "Office se rabta karein: info@ul.edu.pk"
)
