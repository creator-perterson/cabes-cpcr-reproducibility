"""Frozen CABES-v0 score, retained for the factorial comparison."""
from __future__ import annotations
from .bridge_quality import content_tokens


def jaccard(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


def sentence_relevance(question: str, evidence: dict, anchors: dict | None = None) -> float:
    q = content_tokens(question); body = content_tokens(evidence.get("sentence_text", "")); title = content_tokens(evidence.get("document_title", ""))
    overlap = len(q & (body | title)) / max(1, len(q))
    anchor = 1.0 if any(a.get("normalized", "") in evidence.get("sentence_text", "") for a in (anchors or {}).get("anchors", [])) else 0.0
    rank = float(evidence.get("retrieval_rank", 20))
    return min(1.0, .70 * overlap + .20 * anchor + .10 / max(1.0, rank))


def score_chain_v0(question: str, first: dict, second: dict, anchors: dict | None, bridge: dict) -> tuple[float, dict]:
    fa, fb = content_tokens(first.get("sentence_text", "")), content_tokens(second.get("sentence_text", ""))
    rel = max(sentence_relevance(question, first, anchors), sentence_relevance(question, second, anchors))
    increment = 1.0 - jaccard(fa, fb)
    relation = float(bool(fb & set((anchors or {}).get("relation_terms", []))))
    redundancy = jaccard(fa, fb)
    conf = float(bridge.get("bridge_confidence", bridge.get("bridge_match_score", .85)))
    parts = {"anchor_relevance": rel, "explicit_bridge": conf, "information_increment": increment, "relation_match": relation, "redundancy": redundancy, "bridge_risk": 1 - conf}
    score = .30 * rel + .30 * conf + .20 * increment + .20 * relation - .15 * redundancy - .15 * (1 - conf)
    return max(0.0, min(1.0, score)), parts


