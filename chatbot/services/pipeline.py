"""
process_message(text) is the single entry point the Django view (and the
CLI test tool) calls. It wires together: normalize -> extract entities ->
classify intent -> route to the right handler -> return a plain dict.
"""
from . import entity_extractor, intent_classifier, answer_builder
from .config import INTENT_CONFIDENCE_THRESHOLD
from .text_utils import normalize


def process_message(raw_text: str) -> dict:
    query_norm = normalize(raw_text)
    entities = entity_extractor.extract_entities(raw_text)
    intent_result = intent_classifier.classify(query_norm)
    intent, intent_conf, route = intent_result["intent"], intent_result["confidence"], intent_result["route"]

    # Deterministic entity lookups ALWAYS get first chance, regardless of what the intent
    # classifier guessed. This is what stops a misclassified intent (e.g. "grading system kya
    # hai" read as "timetable") from hijacking a question that a clearly-identified entity
    # (program/office/department/bus route/topic keyword) already has an exact answer for.
    answer = answer_builder.entity_override_answer(entities, intent)

    if answer is None:
        if route == "canned":
            answer = {"reply": answer_builder.canned_reply(intent, query_norm), "chunk_id": None, "match_quality": 1.0, "verified": True}
        elif route.startswith("sql:bus"):
            answer = answer_builder.handle_bus_schedule(entities)
        elif route.startswith("sql:timetable"):
            answer = answer_builder.handle_timetable()
        elif intent_conf < INTENT_CONFIDENCE_THRESHOLD:
            # not confident about intent at all -> plain semantic search, no type hint
            answer = answer_builder.semantic_answer(query_norm, "chroma:", entities, intent)
        else:
            answer = answer_builder.semantic_answer(query_norm, route, entities, intent)

    return {
        "reply": answer["reply"],
        "intent": intent,
        "intent_confidence": intent_conf,
        "entities": entities,
        "matched_chunk_id": answer.get("chunk_id"),
        "match_quality": answer.get("match_quality"),
        "answer_verified": answer.get("verified"),
    }
