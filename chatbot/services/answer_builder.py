"""
Turns (intent, entities, retrieved chunks) into the final reply.

Routing (from intents.json's "route" field) is treated as a soft hint,
not a strict query language:
  - "canned"            -> fixed reply, no retrieval
  - "sql:..."           -> answered from the relational DB directly
                            (bus_schedule is LIVE now because BusRoute data
                            already exists; timetable returns a
                            "coming in Module 2" message because that data
                            doesn't exist yet)
  - "chroma:id=X"        -> fetch that one chunk by id directly
  - "chroma:type=X..."   -> semantic search, softly re-ranked by whether a
                            retrieved chunk's type matches X and whether an
                            extracted entity's canonical name appears in the
                            chunk's title/content
"""
import datetime
import json
import random
import re
from functools import lru_cache

from . import vector_store
from .config import RETRIEVAL_CONFIDENCE_THRESHOLD, RETRIEVAL_TOP_N, FALLBACK_REPLY, DATA_DIR

PROGRAMS_FILE = DATA_DIR / "programs.json"

GREETINGS = [
    "Walaikum Assalam! Main University of Layyah ka assistant hoon — admission, fees, "
    "departments, bus schedule ya kisi bhi office ke baare mein poochh sakte hain.",
    "Hello! Kis cheez mein madad chahiye — admission, fee, timetable ya bus schedule?",
]
THANKS = ["Khushi hui madad kar ke! Aur kuch poochna ho to batayein.", "Welcome! Koi aur sawal ho to zaroor poochein."]

TIMETABLE_NOT_READY = (
    "Class timetable abhi is system mein add nahi hua — yeh Module 2 mein aayega jab "
    "admin dashboard se timetable generate ho jayega. Abhi ke liye apne department ke "
    "notice board ya CMS se check karein."
)


def canned_reply(intent, query_norm):
    if intent == "greeting_smalltalk":
        if re.search(r"\b(thanks|thank you|shukriya|shukria)\b", query_norm):
            return random.choice(THANKS)
        return random.choice(GREETINGS)
    return FALLBACK_REPLY


def _type_hint(route):
    m = re.search(r"type=([a-z_]+)", route)
    return m.group(1) if m else None


def _direct_id(route):
    m = re.search(r"id=([a-zA-Z0-9_]+)", route)
    return m.group(1) if m else None


def _rerank(results, type_hint, entities):
    program_ids = {"program_" + e["id"] for e in entities if e["entity_type"] == "program"}

    def score(r):
        s = r["match_quality"]

        if r["id"] in program_ids:
            s += 0.4

        if type_hint:
            if r["type"] == type_hint:
                s += 0.15
            else:
                s -= 0.12  # mild penalty for a type mismatch when we have a specific hint

        title_hay = r["title"].lower()
        content_hay = r["content"].lower()
        for e in entities:
            term = e["canonical"].lower()
            # Campus names show up in almost every bus-route title/content as the start or end
            # point, so a "campus" entity match there is a near-meaningless signal - skip it,
            # unless we're actually looking for transport info (type_hint == "bus").
            if e["entity_type"] == "campus" and r["type"] == "bus" and type_hint != "bus":
                continue
            if term in title_hay:
                s += 0.2
            elif term in content_hay:
                s += 0.08

        return s

    return sorted(results, key=score, reverse=True)


@lru_cache(maxsize=1)
def _load_programs():
    return json.loads(PROGRAMS_FILE.read_text(encoding="utf-8"))


def _money(n):
    return f"{n:,}"


def _unconfirmed_note():
    return (
        "\n\n(Note: yeh maloomat abhi university se double-confirm honi baqi hai, "
        "isliye possible hai ke yeh thori out-of-date ho.)"
    )


def _program_fee_reply(p, shift=None):
    if not p["fee"]:
        return (
            f"{p['name']} ki fee abhi university data mein confirm nahi hai. "
            f"Barah-e-meherbani Admission Office se maloom karein (info@ul.edu.pk)."
        )
    fg = p["fee"]
    shifts = [shift] if (shift and fg.get(shift)) else [s for s in ("morning", "afternoon") if fg.get(s)]
    parts = [f"{p['name']} ki 2026 fee (PKR):"]
    for sh in shifts:
        s = fg.get(sh)
        if s:
            sem_txt = ", ".join(f"Sem {i+1}: {_money(x)}" for i, x in enumerate(s["semesters"]))
            parts.append(f"{sh.capitalize()} shift total {_money(s['total'])} ({sem_txt}).")
    reply = " ".join(parts)
    if p["fee_status"] != "confirmed":
        reply += _unconfirmed_note()
    return reply


def _program_eligibility_reply(p):
    if not p["eligibility"]:
        return (
            f"{p['name']} ke liye eligibility criteria abhi university data mein confirm nahi hai. "
            f"Barah-e-meherbani Admission Office se maloom karein (info@ul.edu.pk)."
        )
    reply = f"{p['name']} ke liye eligibility: {p['eligibility']}"
    if p["merit_formula"]:
        reply += f" Merit formula: {p['merit_formula']}."
    if not p["verified"]:
        reply += _unconfirmed_note()
    return reply


def _program_overview_reply(p):
    reply = (
        f"{p['name']}" + (f" ({p['short_name']})" if p['short_name'] else "") +
        f" {p['department']}, {p['faculty']} mein offer hoti hai. Type: {p['type']}. Duration: {p['duration']}."
    )
    if p.get("campus"):
        reply += f" Yeh {p['campus']} par located hai ({p['campus_address']})."
    if p["eligibility"]:
        reply += f" Eligibility: {p['eligibility']}"
    if not p["verified"]:
        reply += _unconfirmed_note()
    return reply


def program_fact_answer(program_id, intent, entities=None):
    """Short, targeted reply built from structured program data (not the full chunk text)."""
    programs = _load_programs()
    p = programs.get(program_id)
    if not p:
        return None

    if intent == "fee":
        shift_entity = next((e for e in (entities or []) if e["entity_type"] == "shift"), None)
        reply = _program_fee_reply(p, shift_entity["id"] if shift_entity else None)
    elif intent == "eligibility":
        reply = _program_eligibility_reply(p)
    else:
        reply = _program_overview_reply(p)

    return {"reply": reply, "chunk_id": "program_" + program_id, "match_quality": 1.0, "verified": p["verified"] and p["fee_status"] == "confirmed"}


def _fetch_chunk_meta(chunk_id):
    try:
        coll = vector_store._collection(create_if_missing=False)
        got = coll.get(ids=[chunk_id])
        if not got["ids"]:
            return None
        return got["metadatas"][0]
    except Exception:
        return None


def _get_chunk_by_id(chunk_id):
    meta = _fetch_chunk_meta(chunk_id)
    if not meta:
        return None
    reply = meta["content"]
    if not meta.get("verified", True):
        reply += _unconfirmed_note()
    return {"reply": reply, "chunk_id": chunk_id, "match_quality": 1.0, "verified": meta.get("verified", True)}


# Intents that are clearly NOT about a specific program's facts, even if a program name
# happens to appear in the message (e.g. "BSCS students ke liye bus kab hai"). For every other
# intent - including ones the classifier gets wrong, like "eligibility" misread as
# "admission_process" - naming a program should go straight to that program's own data rather
# than trusting the (fragile) intent/route text to pick the right chunk.
_PROGRAM_OVERRIDE_EXCLUDED_INTENTS = {
    "bus_schedule", "bus_route", "contact", "leadership", "hostel",
    "rules_policies", "campus_life", "greeting_smalltalk",
}

# Same idea as the program override, for named offices/leadership roles. Each office id (from
# aliases.json) maps to its "info" chunk and, where one exists, a separate "contact" chunk.
_OFFICE_CHUNK_MAP = {
    "vc": {"info": "admin_vice_chancellor", "contact": None},
    "registrar": {"info": "admin_registrar", "contact": None},
    "treasurer": {"info": "admin_treasurer", "contact": None},
    "exams": {"info": "admin_controller_of_examinations", "contact": None},
    "qec": {"info": "qec_overview", "contact": None},
    "library": {"info": "library_info", "contact": "library_contact"},
    "medical": {"info": "medical_info", "contact": "medical_contact"},
    "scholarships": {"info": "scholarship_info", "contact": "scholarship_contact"},
    "transport": {"info": "transport_info", "contact": "transport_contact"},
    "faculty_hostel": {"info": "faculty_hostel_info", "contact": None},
    "admission_office": {"info": "admission_process", "contact": "admission_contact"},
}

# Office/department questions should not be hijacked by these intents even if the entity still
# matched (e.g. a department name inside a bus-related sentence).
_OFFICE_DEPT_EXCLUDED_INTENTS = {"bus_schedule", "bus_route", "greeting_smalltalk"}

# bus_route (an exact route number) and topic (a collision-free keyword match to one specific
# chunk) are unambiguous enough that almost nothing should override them - only skip for
# small talk, where there's no real question to answer anyway.
_UNAMBIGUOUS_OVERRIDE_EXCLUDED_INTENTS = {"greeting_smalltalk"}


def office_fact_answer(office_id, intent):
    chunk_ids = _OFFICE_CHUNK_MAP.get(office_id)
    if not chunk_ids:
        return None
    preferred = chunk_ids.get("contact") if intent == "contact" else chunk_ids.get("info")
    chunk_id = preferred or chunk_ids.get("info") or chunk_ids.get("contact")
    if not chunk_id:
        return None
    return _get_chunk_by_id(chunk_id)


def _programs_in_department(department_name):
    return [p for p in _load_programs().values() if p["department"] == department_name]


def department_fact_answer(department_id, intent=None, entities=None):
    meta = _fetch_chunk_meta("dept_" + department_id)
    if not meta:
        return None

    if intent == "fee":
        progs = _programs_in_department(meta["title"])
        if len(progs) == 1:
            direct = program_fact_answer(progs[0]["program_id"], "fee", entities)
            if direct:
                return direct
        elif len(progs) > 1:
            lines = []
            for p in progs:
                if p["fee"] and p["fee"].get("morning"):
                    lines.append(f"{p['name']}: {_money(p['fee']['morning']['total'])} (morning shift total)")
                else:
                    lines.append(f"{p['name']}: fee confirm nahi hai")
            reply = (
                f"{meta['title']} mein yeh programs hain, har ek ki fee alag hai: " + "; ".join(lines) +
                ". Kis program ka naam bata kar us ka poora semester-wise breakdown pooch sakte hain."
            )
            return {"reply": reply, "chunk_id": "dept_" + department_id, "match_quality": 1.0, "verified": True}

    return _get_chunk_by_id("dept_" + department_id)


def bus_route_fact_answer(route_id):
    return _get_chunk_by_id("bus_route_" + route_id)


def topic_fact_answer(chunk_id):
    """Generic deterministic lookup for every chunk that isn't a program/office/department/bus
    route but still has its own distinctive, collision-free keywords (FAQs, fee groups, faculties,
    vision/mission, campuses overview, contact directory, etc.) - see aliases.json entity_type
    'topic', whose id IS the target chunk id."""
    return _get_chunk_by_id(chunk_id)


def entity_override_answer(entities, intent):
    """The single entry point for deterministic, entity-driven answers. Tried BEFORE any
    intent/route-based branching (including 'this looks like a timetable/bus question'), so a
    clearly-identified entity (a program, an office, a department, an exact bus route number, or
    a collision-free topic keyword) always wins over a misclassified intent. Returns None if
    nothing applies, so the caller falls through to route-based / semantic search."""
    program_entities = [e for e in entities if e["entity_type"] == "program"]
    if program_entities and intent not in _PROGRAM_OVERRIDE_EXCLUDED_INTENTS:
        direct = program_fact_answer(program_entities[0]["id"], intent, entities)
        if direct:
            return direct

    if intent not in _OFFICE_DEPT_EXCLUDED_INTENTS:
        office_entities = [e for e in entities if e["entity_type"] == "office"]
        if office_entities:
            direct = office_fact_answer(office_entities[0]["id"], intent)
            if direct:
                return direct

        dept_entities = [e for e in entities if e["entity_type"] == "department"]
        if dept_entities:
            direct = department_fact_answer(dept_entities[0]["id"], intent, entities)
            if direct:
                return direct

    if intent not in _UNAMBIGUOUS_OVERRIDE_EXCLUDED_INTENTS:
        bus_route_entities = [e for e in entities if e["entity_type"] == "bus_route"]
        if bus_route_entities:
            direct = bus_route_fact_answer(bus_route_entities[0]["id"])
            if direct:
                return direct

        topic_entities = [e for e in entities if e["entity_type"] == "topic"]
        if topic_entities:
            direct = topic_fact_answer(topic_entities[0]["id"])
            if direct:
                return direct

    return None


def semantic_answer(query_norm, route, entities, intent=None):
    direct_id = _direct_id(route)
    if direct_id:
        direct = _get_chunk_by_id(direct_id)
        if direct:
            return direct

    results = vector_store.query(query_norm, n_results=RETRIEVAL_TOP_N)
    if not results:
        return {"reply": FALLBACK_REPLY, "chunk_id": None, "match_quality": 0.0, "verified": None}

    type_hint = _type_hint(route)
    results = _rerank(results, type_hint, entities)
    best = results[0]

    if best["match_quality"] < RETRIEVAL_CONFIDENCE_THRESHOLD:
        return {"reply": FALLBACK_REPLY, "chunk_id": best["id"], "match_quality": best["match_quality"], "verified": best["verified"]}

    reply = best["content"]
    if not best["verified"]:
        reply += (
            "\n\n(Note: yeh maloomat abhi university se double-confirm honi baqi hai, "
            "isliye possible hai ke yeh thori out-of-date ho.)"
        )
    return {"reply": reply, "chunk_id": best["id"], "match_quality": best["match_quality"], "verified": best["verified"]}


def _entity_value(entities, etype):
    for e in entities:
        if e["entity_type"] == etype:
            return e
    return None


def handle_bus_schedule(entities):
    """Live 'next bus' answer using campusinfo.BusRoute, if that app is installed."""
    try:
        from campusinfo.models import BusRoute
    except Exception:
        return {"reply": "Bus schedule database abhi connect nahi hai is deployment mein.", "chunk_id": None, "match_quality": 0.0, "verified": False}

    now = datetime.datetime.now().time()
    stop_entity = _entity_value(entities, "bus_stop")
    campus_entity = _entity_value(entities, "campus")

    qs = BusRoute.objects.all()
    if stop_entity:
        qs = qs.filter(starting_point__icontains=stop_entity["canonical"]) | BusRoute.objects.filter(stops__icontains=stop_entity["canonical"])
    elif campus_entity:
        qs = qs.filter(starting_point__icontains=campus_entity["canonical"])

    upcoming = sorted([r for r in qs if r.departure_time >= now], key=lambda r: r.departure_time)
    if not upcoming:
        upcoming = sorted(qs, key=lambda r: r.departure_time)  # none left today -> show the day's first one
        prefix = "Aaj ke liye is waqt ke baad koi bus nahi bachi. Kal ki pehli bus: "
    else:
        prefix = "Agli bus: "

    if not upcoming:
        return {"reply": "Is stop/campus ke liye koi bus route record nahi mila.", "chunk_id": None, "match_quality": 0.0, "verified": False}

    r = upcoming[0]
    reply = (f"{prefix}Route {r.route_id}, {r.starting_point} se {r.destination} ke liye, "
              f"{r.departure_time.strftime('%I:%M %p')} par (driver: {r.driver_name}).")
    return {"reply": reply, "chunk_id": f"bus_route_{r.route_id}", "match_quality": 1.0, "verified": r.verified}


def handle_timetable():
    return {"reply": TIMETABLE_NOT_READY, "chunk_id": None, "match_quality": 1.0, "verified": True}
