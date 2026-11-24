"""Question-target relation rules used by the V1 chain scorer."""
from __future__ import annotations
from .bridge_quality import content_tokens, normalize

RELATION_TERMS = {
    "birth": {"born", "birth", "birthday", "origin", "country"},
    "death": {"died", "death", "dead", "buried"},
    "director": {"director", "directed", "filmmaker"},
    "author": {"author", "wrote", "written", "novelist"},
    "location": {"located", "location", "city", "country", "where", "based"},
    "date": {"when", "year", "date", "released", "premiered"},
    "count": {"many", "number", "how", "count"},
    "organization": {"company", "owned", "owner", "parent", "founded"},
    "membership": {"member", "band", "joined", "played", "starred", "appeared"},
}


def question_relations(question: str, anchors: dict | None = None) -> list[str]:
    words = content_tokens(question)
    found = [name for name, terms in RELATION_TERMS.items() if words & terms]
    if anchors:
        found.extend(x for x in anchors.get("relations", []) if x != "UNKNOWN")
    return sorted(set(found)) or ["UNKNOWN"]


def target_relation_alignment(question: str, second: dict, anchors: dict | None = None) -> dict:
    relations = question_relations(question, anchors)
    words = content_tokens(second.get("sentence_text", ""))
    hits = {r: sorted(words & RELATION_TERMS[r]) for r in relations if r in RELATION_TERMS and words & RELATION_TERMS[r]}
    if hits:
        score = min(1.0, 0.55 + 0.15 * len(hits))
        status = "ALIGNED" if len(hits) == 1 else "AMBIGUOUS"
    else:
        score, status = 0.0, "UNKNOWN"
    return {"relations_considered": relations, "matched_relation_terms": hits, "target_relation_score": score, "target_relation_status": status}


