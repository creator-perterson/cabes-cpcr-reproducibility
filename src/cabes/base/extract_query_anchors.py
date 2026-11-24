"""Small deterministic anchor extractor used by compatibility callers."""
from .bridge_quality import content_tokens, title_alias
from .target_relation_alignment import question_relations

def extract_query_anchors(question, evidence):
    q = question.casefold()
    anchors = []
    for title in sorted({e.get("document_title", "") for e in evidence}):
        alias = title_alias(title)
        if alias and alias in q:
            anchors.append({"text": title, "normalized": alias, "type": "SOURCE_TITLE_IN_QUERY", "validation_status": "EXACT_STRING"})
    return {"anchors": anchors, "keywords": sorted(content_tokens(question)), "relations": question_relations(question), "relation_terms": sorted(content_tokens(question)), "status": "KNOWN" if anchors else "UNKNOWN"}


