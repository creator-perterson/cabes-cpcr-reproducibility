"""Lightweight, role-aware evidence relation extraction without a model."""
from __future__ import annotations
import re
from .bridge_quality import normalize

PATTERNS = [
    ("shops_at", r"(?P<subject>.+?)\s+(?:regularly\s+)?shops?\s+at\s+(?P<object>[^,.;]+)"),
    ("appeared_in", r"(?P<subject>.+?)\s+(?:regularly\s+)?appeared\s+in\s+(?P<object>[^,.;]+)"),
    ("appeared_in", r"(?P<subject>.+?)\s+(?:regularly\s+)?(?:starred|acted)\s+in\s+(?P<object>[^,.;]+)"),
    ("born_in", r"(?P<subject>.+?)\s+(?:was\s+)?born\s+in\s+(?P<object>[^,.;]+)"),
    ("born_on", r"(?P<subject>.+?)\s+(?:was\s+)?born\s+on\s+(?P<object>[^,.;]+)"),
    ("works_for", r"(?P<subject>.+?)\s+works?\s+for\s+(?P<object>[^,.;]+)"),
    ("founded_by", r"(?P<subject>.+?)\s+was\s+founded\s+by\s+(?P<object>[^,.;]+)"),
    ("founded", r"(?P<subject>.+?)\s+founded\s+(?P<object>[^,.;]+)"),
    ("married_to", r"(?P<subject>.+?)\s+married\s+to\s+(?P<object>[^,.;]+)"),
]

def extract_relation_triples(sentence: str) -> list[dict]:
    text = sentence or ""; out=[]
    for predicate, pattern in PATTERNS:
        for m in re.finditer(pattern, text, re.I):
            subject = normalize(m.group("subject")).strip(" -:")
            raw_objects = re.split(r"\s+and\s+", m.group("object"), flags=re.I) if predicate == "appeared_in" else [m.group("object")]
            for raw_obj in raw_objects:
                obj = normalize(raw_obj).strip(" -:")
                if not subject or not obj or subject == obj: continue
                out.append({"subject_entity": subject, "predicate": predicate, "object_entity": obj, "subject_span": m.group("subject").strip(), "predicate_span": text[m.start():m.end()][len(m.group("subject")):].strip(), "object_span": raw_obj.strip(), "direction": "subject_to_object", "extraction_method": "deterministic_role_template", "confidence": 0.9, "status": "VERIFIED", "source_text": text[m.start():m.end()]})
    seen=set(); unique=[]
    for x in out:
        key=(x["subject_entity"],x["predicate"],x["object_entity"])
        if key not in seen: seen.add(key); unique.append(x)
    return unique


