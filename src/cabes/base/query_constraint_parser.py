"""Deterministic decomposition of a question into its answer relation and constraints."""
from __future__ import annotations
import re
from .bridge_quality import content_tokens, normalize, title_alias

ANSWER_TYPES = {
    "actress": "actress", "actor": "actor", "person": "person", "man": "person", "woman": "person",
    "organization": "organization", "company": "organization", "group": "group", "band": "group",
    "city": "location", "country": "location", "location": "location", "place": "location",
    "film": "work", "movie": "work", "book": "work", "date": "date", "year": "year",
}

PRIMARY_PATTERNS = [
    ("shops_at", re.compile(r"\b(?:regularly\s+)?shops?\s+at\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "person", "store"),
    ("born_on", re.compile(r"\bborn\s+on\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "person", "date"),
    ("born_in", re.compile(r"\bborn\s+in\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "person", "location"),
    ("located_in", re.compile(r"\b(?:located|based)\s+in\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "entity", "location"),
    ("directed_by", re.compile(r"\b(?:directed\s+by|who\s+directed)\b", re.I), "ANSWER_ENTITY_TO_ANCHOR", "work", "person"),
    ("written_by", re.compile(r"\b(?:written\s+by|who\s+wrote)\b", re.I), "ANSWER_ENTITY_TO_ANCHOR", "work", "person"),
    ("appeared_in", re.compile(r"\b(?:appeared|starred|acted)\s+in\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "person", "work"),
    ("works_for", re.compile(r"\bworks?\s+for\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "person", "organization"),
    ("married_to", re.compile(r"\bmarried\s+to\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "person", "person"),
    ("founded_by", re.compile(r"\bfounded\s+by\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "organization", "person"),
    ("member_of", re.compile(r"\b(?:member\s+of|joined)\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "person", "organization"),
    ("part_of", re.compile(r"\b(?:part\s+of|belongs\s+to)\s+", re.I), "ANSWER_ENTITY_TO_ANCHOR", "entity", "group"),
]

def answer_type(question: str) -> str:
    q = question.casefold().strip()
    m = re.search(r"\b(?:which|what)\s+([a-z]+)\b", q)
    if m and m.group(1) in ANSWER_TYPES: return ANSWER_TYPES[m.group(1)]
    if q.startswith("where "): return "location"
    if q.startswith("when "): return "date"
    if re.match(r"^(who|whom)\b", q): return "person"
    return "UNKNOWN"

def _object_after(question: str, match: re.Match) -> str:
    tail = question[match.end():]
    tail = re.split(r"[?;,.]", tail, maxsplit=1)[0]
    tail = re.split(r"\b(?:regularly|that|who|which|and)\b", tail, maxsplit=1, flags=re.I)[0]
    return normalize(tail.strip())

def _title_entities(question: str, evidence: list[dict]) -> list[dict]:
    q = normalize(question); out=[]
    for title in sorted({e.get("document_title", "") for e in evidence}, key=lambda x:(-len(x), x)):
        alias = title_alias(title)
        if alias and _contains_normalized_phrase(question, alias):
            out.append({"text": title, "normalized": alias, "role": "query_entity", "source": "evidence_title_exact"})
    out.sort(key=lambda x: normalize(question).find(normalize(x["text"])))
    return out

def _contains_normalized_phrase(question: str, phrase: str) -> bool:
    words = [x for x in normalize(phrase).split() if x]
    if not words: return False
    pattern = r"(?<!\w)" + r"\W+".join(re.escape(x) for x in words) + r"(?!\w)"
    return bool(re.search(pattern, normalize(question)))

def decompose_query(question_id: str, question: str, evidence: list[dict]) -> dict:
    anchors = _title_entities(question, evidence)
    q = question.casefold(); primary = None; candidates=[]
    for predicate, pattern, direction, subject_role, object_role in PRIMARY_PATTERNS:
        m = pattern.search(question)
        if not m: continue
        obj = _object_after(question, m) if predicate in {"shops_at", "born_in", "born_on", "located_in", "works_for", "married_to", "member_of", "part_of"} else ""
        candidate = {"predicate": predicate, "subject_role": subject_role, "object_role": object_role, "subject_anchor": "ANSWER_ENTITY", "object_anchor": obj or None, "relation_direction": direction, "source_span": m.group(0).strip(), "confidence": 0.9, "status": "VERIFIED", "lexical_patterns": [m.group(0).strip()], "supported_surface_forms": [m.group(0).strip()]}
        candidates.append(candidate)
    # The first explicit answer-bearing relation is primary.  Constraint
    # prepositional phrases are parsed separately below.
    if candidates:
        primary = candidates[0]
        if primary.get("object_anchor"):
            primary["object_anchor"] = {"text": primary["object_anchor"], "normalized": primary["object_anchor"]}
    constraints=[]
    primary_object = (primary or {}).get("object_anchor") or {}
    for ent in anchors:
        if primary_object and ent["normalized"] == primary_object.get("normalized"): continue
        if primary and primary["predicate"] == "shops_at":
            span = re.search(r"(?:on|in)\s+" + r"\W+".join(re.escape(x) for x in ent["normalized"].split()), q)
            if span and _contains_normalized_phrase(question, ent["normalized"]):
                constraints.append({"predicate": "appeared_in", "subject_role": "ANSWER_ENTITY", "object_role": "work", "subject_anchor": "ANSWER_ENTITY", "entity_anchor": ent, "relation_direction": "ANSWER_ENTITY_TO_ANCHOR", "source_span": question[span.start():span.end()], "status": "VERIFIED", "confidence": 0.85})
    status = "VERIFIED" if primary else "UNKNOWN"
    if len(candidates) > 1 and not (primary and primary["predicate"] == "shops_at"):
        status = "AMBIGUOUS"
    atype = answer_type(question)
    if atype == "UNKNOWN" and primary: atype = "person" if primary["subject_role"] == "person" else primary["object_role"]
    spans = [primary["source_span"]] if primary else []
    spans += [c["source_span"] for c in constraints]
    relation_args = {"subject": {"role": "ANSWER_ENTITY", "normalized": "ANSWER_ENTITY"} if primary else None, "object": primary.get("object_anchor") if primary else None}
    return {"question_id": question_id, "question_text": question, "answer_slot": "ANSWER_ENTITY", "answer_type": atype, "primary_relation": primary or {"status": "UNKNOWN"}, "constraints": constraints, "query_anchor_entities": anchors, "relation_predicate_candidates": candidates, "relation_direction": primary.get("relation_direction", "UNKNOWN") if primary else "UNKNOWN", "relation_arguments": relation_args, "expected_answer_type": atype, "answer_constraints": constraints, "relation_evidence_spans": spans, "extraction_method": "fixed_relation_templates_with_title_constraints", "extraction_confidence": 0.9 if status == "VERIFIED" else 0.45 if status == "AMBIGUOUS" else 0.0, "relation_status": status}


