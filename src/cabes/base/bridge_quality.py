"""Deterministic, source-grounded bridge diagnostics.

The registry is intentionally local to the frozen evidence pool.  It does not
claim that two titles denote the same real-world entity unless the text gives a
verifiable title/alias match.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

STOP = set("a an and are as at be been being both by did do does for from had has have how in into is it its many of on or that the their them they this those to was were what when where which who whom whose why will with would".split())
GENERIC = set("united states united kingdom new york city world american british english film movie university company school national international country province".split())


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").casefold().strip()


def tokens(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", normalize(text))


def content_tokens(text: str) -> set[str]:
    return {w for w in tokens(text) if w not in STOP and len(w) > 1}


def title_alias(title: str) -> str:
    return " ".join(tokens(re.sub(r"\s*\([^)]*\)$", "", title)))


def _contains_phrase(text: str, phrase: str) -> bool:
    hay = " ".join(tokens(text))
    needle = " ".join(tokens(phrase))
    return bool(needle) and (f" {needle} " in f" {hay} ")


def _mentions(text: str, alias: str) -> bool:
    return _contains_phrase(text, alias)


def build_source_registry(evidence: list[dict]) -> dict:
    """Build a deterministic title/alias registry and document frequencies."""
    docs = {}
    for e in evidence:
        docs.setdefault(e["document_id"], {"document_id": e["document_id"], "title": e["document_title"], "alias": title_alias(e["document_title"])})
    for d in docs.values():
        d["alias_tokens"] = sorted(content_tokens(d["alias"]))
        d["is_generic"] = not (set(d["alias_tokens"]) - GENERIC)
        d["mentioning_documents"] = sorted({e["document_id"] for e in evidence if _mentions(e["sentence_text"], d["alias"])})
    return docs


def bridge_quality(first: dict, second: dict, source_registry: dict, *, question: str = "") -> dict:
    """Return auditable bridge evidence for an ordered sentence pair.

    Scores are fixed rules: exact title mention is strongest, token-level alias
    matches are weaker, ambiguous/high-frequency aliases are penalised, and no
    match remains UNKNOWN.  ``second`` is expected to be from the document whose
    title is being mentioned by ``first``.
    """
    first_text = f"{first.get('sentence_text', '')} {first.get('document_title', '')}"
    second_text = f"{second.get('sentence_text', '')} {second.get('document_title', '')}"
    first_doc = source_registry.get(first.get("document_id"), {})
    second_doc = source_registry.get(second.get("document_id"), {})
    alias = second_doc.get("alias", title_alias(second.get("document_title", "")))
    alias_set = set(second_doc.get("alias_tokens", content_tokens(alias)))
    first_set = content_tokens(first_text)
    exact = _mentions(first_text, alias)
    overlap = alias_set & first_set
    non_generic = overlap - GENERIC
    frequency = len(second_doc.get("mentioning_documents", [])) / max(1, len(source_registry))
    ambiguous = len(non_generic) == 0 or frequency > 0.35 or len(alias_set) <= 1
    if exact and not ambiguous:
        match_type, base = "EXACT_NORMALIZED_TITLE", 1.0
        status = "VERIFIED"
    elif exact and ambiguous:
        match_type, base = "AMBIGUOUS_ALIAS", 0.45
        status = "UNCERTAIN"
    elif non_generic and not ambiguous:
        match_type, base = "TITLE_ALIAS_TOKEN_OVERLAP", 0.65
        status = "UNCERTAIN"
    elif overlap:
        match_type, base = "GENERIC_OR_ACCIDENTAL_OVERLAP", 0.15
        status = "UNCERTAIN"
    else:
        match_type, base = "NO_VERIFIABLE_BRIDGE", 0.0
        status = "UNKNOWN"
    # A title appearing in the first sentence is source identity evidence.  The
    # first document is retained for provenance even when it is not linked.
    source_identity_verified = bool(second_doc.get("document_id")) and bool(alias)
    ambiguity_penalty = 0.35 if ambiguous and base > 0 else 0.0
    score = max(0.0, min(1.0, base - ambiguity_penalty))
    return {
        "bridge_match_score": score,
        "ambiguity_penalty": ambiguity_penalty,
        "source_identity_verified": source_identity_verified and status != "UNKNOWN",
        "match_type": match_type,
        "evidence_span": alias if exact or overlap else "",
        "uncertainty_status": status,
        "bridge_key": alias,
        "source_pair": [first.get("document_id"), second.get("document_id")],
        "alias_frequency": frequency,
        "first_source_title": first_doc.get("title", first.get("document_title", "")),
    }


def discover_structural_bridges(evidence: list[dict], *, anchor_uids: set[str] | None = None) -> list[dict]:
    """Freeze the candidate graph before either scoring version is applied."""
    registry = build_source_registry(evidence)
    by_doc = {}
    for e in evidence:
        by_doc.setdefault(e["document_id"], []).append(e)
    edges = []
    for a in sorted(evidence, key=lambda x: (x.get("retrieval_rank", 0), x.get("sentence_uid", ""))):
        if anchor_uids is not None and a["sentence_uid"] not in anchor_uids:
            continue
        for doc_id, second_doc in sorted(registry.items()):
            if doc_id == a["document_id"]:
                continue
            # Structural discovery uses title/alias mention only.  It does not
            # apply V1 quality thresholds, keeping all arms on one graph.
            alias = second_doc["alias"]
            if not _mentions(a["sentence_text"], alias):
                continue
            for b in sorted(by_doc[doc_id], key=lambda x: (x.get("original_sentence_index", 0), x["sentence_uid"])):
                bridge = bridge_quality(a, b, registry)
                edges.append({"anchor_evidence": a["sentence_uid"], "target_evidence": b["sentence_uid"], **bridge})
    # Include uncertain title-token edges only if exact structural title mention
    # exists; deduplicate by UID pair and make ordering deterministic.
    seen = set()
    out = []
    for e in edges:
        k = (e["anchor_evidence"], e["target_evidence"])
        if k not in seen:
            seen.add(k); out.append(e)
    return out



