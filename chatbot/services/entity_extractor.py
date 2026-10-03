"""
Finds known entities (department, program, bus_stop, office, campus,
shift, program_type) inside a user's message using the aliases.json
lookup table built during data prep. Pure string matching - no model
needed, so this is instant and 100% deterministic.

Matching strategy:
  1. Normalize the query the same way aliases were lowercased.
  2. Check every alias as a whole-word/phrase match (regex word
     boundaries), longest alias first, so "bba it" wins over "bba" when
     both would otherwise match.
  3. Once a span of the query is consumed by a match, don't let a
     shorter alias match inside that same span again.
"""
import json
import re
from functools import lru_cache

from .config import ALIASES_FILE, CHUNKS_FILE
from .text_utils import normalize

_ROUTE_NUM_RE = re.compile(r"route\s*#?\s*(\d+)|#\s*(\d+)\s*route", re.IGNORECASE)


@lru_cache(maxsize=1)
def _valid_bus_route_ids():
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    return {c["id"].rsplit("_", 1)[-1] for c in chunks if c["id"].startswith("bus_route_")}


def _extract_bus_route_entities(norm_query):
    """'route 3', 'route no 7', '#5 route' -> a bus_route entity, but only for route numbers
    that actually exist in our data (so 'route 99' doesn't falsely match anything)."""
    valid_ids = _valid_bus_route_ids()
    found, seen = [], set()
    for m in _ROUTE_NUM_RE.finditer(norm_query):
        num = m.group(1) or m.group(2)
        if num in valid_ids and num not in seen:
            found.append({"entity_type": "bus_route", "id": num, "canonical": f"Route {num}", "matched_text": m.group(0)})
            seen.add(num)
    return found


@lru_cache(maxsize=1)
def _load_aliases():
    raw = json.loads(ALIASES_FILE.read_text(encoding="utf-8"))
    # sort by alias length (longest first) so multi-word aliases are tried first
    entries = []
    for e in raw:
        for alias in e["aliases"]:
            entries.append((alias, e["entity_type"], e["id"], e["canonical"]))
    entries.sort(key=lambda x: len(x[0]), reverse=True)
    return entries


def extract_entities(query: str):
    """Returns a list of dicts: {entity_type, id, canonical, matched_text}."""
    norm = normalize(query)
    if not norm:
        return []

    entries = _load_aliases()
    consumed = [False] * (len(norm) + 1)
    found = []
    seen = set()

    for alias, etype, eid, canonical in entries:
        if len(alias) < 2:
            continue
        for m in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", norm):
            start, end = m.start(), m.end()
            if any(consumed[start:end]):
                continue
            key = (etype, eid)
            if key in seen:
                consumed[start:end] = [True] * (end - start)
                continue
            found.append({
                "entity_type": etype, "id": eid, "canonical": canonical,
                "matched_text": alias,
            })
            seen.add(key)
            consumed[start:end] = [True] * (end - start)

    found.extend(_extract_bus_route_entities(norm))
    return found
