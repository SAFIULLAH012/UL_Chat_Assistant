# chatbot — offline University of Layyah chatbot (no API key)

Answers from the data you provided (fees, eligibility, offices, FAQs,
bus routes) using a local embedding model (MiniLM) + ChromaDB for
semantic search, plus a rule-based entity extractor for Roman Urdu
department/program/bus-stop names. **No external API, no cost, no
rate limit.**

What's LIVE in this phase:
- Fees, eligibility, programs/departments, offices (library, medical,
  transport, scholarships, QEC, faculty hostel), FAQs, bus routes
  (static info) — answered from `chatbot_chunks.json` via semantic search.
- **"Next bus" queries are answered live** from the `BusRoute` table
  (built in the previous phase) using the current time — this one
  isn't a canned chunk, it's a real lookup.
- Greetings/thanks — canned replies.

What's NOT live yet (by design — later modules):
- `timetable` intent (e.g. "Sir Ali ki class kab hai") replies with a
  "coming in Module 2" message. There is no teacher/section/room data
  yet for it to answer from.

## 1. Install

Copy the `chatbot/` folder into your Django project (next to `manage.py`,
alongside the `campusinfo` app from the previous phase — it's optional
but gives the bus-schedule feature live data).

```bash
pip install -r requirements-chatbot.txt --break-system-packages
```

In `settings.py`:

```python
INSTALLED_APPS = [
    ...
    "campusinfo",   # optional but recommended, enables live bus schedule
    "chatbot",
]
```

In your project's root `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    ...
    path("api/", include("chatbot.urls")),
]
```

## 2. Build the index (one-time, then after any content change)

```bash
python manage.py build_chatbot_index
```

First run downloads the MiniLM model (~400MB, needs internet **once**).
Every run after that is fully offline. This also warms the intent
classifier's embedding cache (`chatbot/data/intents_cache.json`).

If you've started editing chatbot content in the `campusinfo` admin's
**Chatbot Chunks** table instead of the JSON file, rebuild from there:

```bash
python manage.py build_chatbot_index --source db
```

## 3. Test from the terminal (before your frontend is wired up)

```bash
python manage.py chat_cli
```

```
You: bscs ki fees kitni hai
Bot: BS Computer Science is offered by the Department of Computer
Science, Faculty of Computing... Fee structure 2026 (PKR) — Morning
shift total 302,517 (semester-wise: 1st: 45,500, ...)
  [intent=fee conf=0.78 match_quality=0.91 chunk=program_bs_computer_science entities=[('program', 'BS Computer Science')]]
```

The bracketed debug line is what you use for calibration (step 5).

## 4. Wire up your existing frontend

Single endpoint:

```
POST /api/chat/
Content-Type: application/json
{"message": "sugar mills moor se bus kab jati hai"}
```

```json
{
  "reply": "Agli bus: Route 3, Sugar Mills Moor se City Campus ke liye, 07:45 AM par (driver: ...).",
  "intent": "bus_schedule",
  "intent_confidence": 0.74,
  "entities": [{"entity_type": "bus_stop", "id": "sugar_mills_moor", "canonical": "Sugar Mills Moor", "matched_text": "sugar mills moor"}],
  "matched_chunk_id": "bus_route_3",
  "match_quality": 1.0,
  "answer_verified": true
}
```

If your frontend is on a different origin, install `django-cors-headers`
and allow it — `chat()` in `views.py` is `csrf_exempt` already since
it's a stateless JSON API, but CORS is a separate browser-side check.

## 5. Calibrate the thresholds (do this before showing it to anyone)

This was built without internet access to the real embedding model, so
`INTENT_CONFIDENCE_THRESHOLD` and `RETRIEVAL_CONFIDENCE_THRESHOLD` in
`chatbot/services/config.py` are starting guesses, not measured values.

1. Run `chat_cli` with ~30 realistic questions — mix clean English,
   Roman Urdu, and a few typos.
2. Watch the `conf=` and `match_quality=` numbers in the debug line.
3. If a question you'd expect to be answered instead gets the
   "mujhe pakka jawab nahi mil saka" fallback, lower the relevant
   threshold slightly. If it confidently answers something it
   shouldn't (wrong chunk), raise it.
4. Re-run `chat_cli` — no rebuild needed, thresholds are read live.

## 6. What's deliberately simple right now (fix later, not urgent)

- **Routing is a soft hint, not a strict filter** — `semantic_answer()`
  re-ranks by type/entity match rather than hard-filtering ChromaDB.
  This is more forgiving of imperfect intent classification; tighten
  it later if you see wrong-category answers slipping through.
- **Alias matching is exact substring, not fuzzy** — a genuine typo like
  "libary" won't match "library" yet. Add `rapidfuzz` and a fallback
  fuzzy pass in `entity_extractor.py` if this turns out to matter.
- **No conversation memory** — each message is answered independently.
  Add a `session_id` + simple context dict (last department/program
  mentioned) once the frontend sends one, so "iski fee?" after "BSCS
  kya hai?" can resolve "iski" to BSCS.

## Files

```
chatbot/
  apps.py
  views.py                      POST /api/chat/, GET /api/chat/health/
  urls.py
  data/
    aliases.json                 entity lookup (dept/program/bus-stop/office names)
    intents.json                 labelled examples for intent classification
    chatbot_chunks.json          the actual answer content
    intents_cache.json           auto-generated embedding cache (gitignore this)
  services/
    config.py                    thresholds, model name, file paths
    model_loader.py               loads MiniLM once, shared by classifier + vector store
    text_utils.py                 query normalization
    entity_extractor.py           alias-based entity matching
    intent_classifier.py          kNN intent classification
    vector_store.py               ChromaDB wrapper
    answer_builder.py             routing logic + reply construction
    pipeline.py                   process_message() - the one function views.py calls
  management/commands/
    build_chatbot_index.py        rebuild the vector index
    chat_cli.py                   terminal test tool
```
