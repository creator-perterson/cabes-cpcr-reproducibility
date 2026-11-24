"""Role- and direction-aware alignment of a decomposed query to two sentences."""
from __future__ import annotations
from .extract_evidence_relations import extract_relation_triples
from .bridge_quality import normalize

def _match(entity: str, target: str) -> bool:
    a, b = " ".join(normalize(entity).replace("&", " ").split()), " ".join(normalize(target).replace("&", " ").split())
    if not a or not b: return False
    return a == b or (len(a.split()) > 1 and a in b) or (len(b.split()) > 1 and b in a)

def _primary_side(demand: dict, evidence: dict, bridge_entity: str | None) -> dict:
    primary = demand.get("primary_relation", {})
    predicate = primary.get("predicate")
    target = (primary.get("object_anchor") or {}).get("normalized", "") if isinstance(primary.get("object_anchor"), dict) else normalize(primary.get("object_anchor", ""))
    triples = extract_relation_triples(evidence.get("sentence_text", ""))
    candidates = [t for t in triples if t["predicate"] == predicate]
    rows=[]; contradicted=False
    for t in candidates:
        subject_ok = bool(bridge_entity and _match(t["subject_entity"], bridge_entity))
        object_ok = bool(target and _match(t["object_entity"], target))
        direction_ok = subject_ok and object_ok
        if not direction_ok and target and _match(t["subject_entity"], target) and bridge_entity and _match(t["object_entity"], bridge_entity): contradicted=True
        rows.append({"triple": t, "predicate_match": True, "subject_match": subject_ok, "object_match": object_ok, "bridge_entity_match": subject_ok, "query_anchor_match": object_ok, "relation_direction_match": direction_ok, "evidence_span": t["source_text"], "match_status": "VERIFIED" if direction_ok else "CONTRADICTED" if contradicted else "UNKNOWN"})
    if not candidates:
        return {"predicate": predicate, "predicate_match": False, "subject_match": False, "object_match": False, "bridge_entity_match": False, "query_anchor_match": False, "relation_direction_match": False, "evidence_span": "", "match_status": "UNKNOWN", "triples": triples, "matches": []}
    best = next((r for r in rows if r["match_status"] == "VERIFIED"), next((r for r in rows if r["match_status"] == "CONTRADICTED"), rows[0]))
    return {**best, "predicate": predicate, "triples": triples, "matches": rows}

def _constraint_side(constraint: dict, evidence: dict, bridge_entity: str | None) -> dict:
    predicate = constraint.get("predicate"); target = (constraint.get("entity_anchor") or {}).get("normalized", "")
    triples = extract_relation_triples(evidence.get("sentence_text", "")); rows=[]
    for t in triples:
        if t["predicate"] != predicate: continue
        subject_ok = bool(bridge_entity and _match(t["subject_entity"], bridge_entity)); object_ok = bool(target and _match(t["object_entity"], target))
        rows.append({"triple": t, "predicate_match": True, "subject_match": subject_ok, "object_match": object_ok, "bridge_entity_match": subject_ok, "query_anchor_match": object_ok, "relation_direction_match": subject_ok and object_ok, "evidence_span": t["source_text"], "match_status": "VERIFIED" if subject_ok and object_ok else "UNKNOWN"})
    return next((r for r in rows if r["match_status"] == "VERIFIED"), rows[0] if rows else {"predicate": predicate, "predicate_match": False, "subject_match": False, "object_match": False, "bridge_entity_match": False, "query_anchor_match": False, "relation_direction_match": False, "evidence_span": "", "match_status": "UNKNOWN", "triple": None})

def align_query_relation_to_chain(question, demand, first, second, bridge):
    # Derive the answer bridge from explicit relation arguments, never from the
    # source-title bridge key.  This prevents one entity from satisfying both roles.
    ta = extract_relation_triples(first.get("sentence_text", "")); tb = extract_relation_triples(second.get("sentence_text", "")); all_triples = ta + tb
    primary = demand.get("primary_relation", {}); predicate = primary.get("predicate")
    subjects = [t["subject_entity"] for t in all_triples if t["predicate"] == predicate]
    bridge_entity = None
    for s in subjects:
        if sum(_match(s, t["subject_entity"]) for t in all_triples if t["predicate"] in {predicate, "appeared_in"}) >= 1:
            bridge_entity = s; break
    first_a = _primary_side(demand, first, bridge_entity); second_a = _primary_side(demand, second, bridge_entity)
    primary_matches = [x for x, name in ((first_a, "first"), (second_a, "second")) if x.get("match_status") == "VERIFIED"]
    primary_sides = [name for x, name in ((first_a, "first"), (second_a, "second")) if x.get("match_status") == "VERIFIED"]
    primary_contradicted = any(x.get("match_status") == "CONTRADICTED" for x in (first_a, second_a))
    constraint_statuses=[]; constraint_sides=[]
    for i, constraint in enumerate(demand.get("constraints", [])):
        a, b = _constraint_side(constraint, first, bridge_entity), _constraint_side(constraint, second, bridge_entity)
        if a.get("match_status") == "VERIFIED": constraint_sides.append({"constraint_index": i, "side": "first", "span": a.get("evidence_span", "")})
        if b.get("match_status") == "VERIFIED": constraint_sides.append({"constraint_index": i, "side": "second", "span": b.get("evidence_span", "")})
        constraint_statuses.append({"constraint_index": i, "predicate": constraint.get("predicate"), "status": "VERIFIED" if a.get("match_status") == "VERIFIED" or b.get("match_status") == "VERIFIED" else "UNKNOWN", "first": a, "second": b})
    constraints_ok = all(x["status"] == "VERIFIED" for x in constraint_statuses)
    bridge_verified = bool(bridge_entity and len(bridge_entity.split()) >= 2 and bridge.get("source_identity_verified") and bridge.get("source_pair"))
    complement = bool(primary_matches) and (not demand.get("constraints") or constraints_ok) and len({x["side"] for x in constraint_sides}) >= 1
    if not demand.get("constraints"): complement = bool(primary_matches)
    if primary_matches and bridge_verified and complement: status = "VERIFIED"
    elif primary_contradicted: status = "CONTRADICTED"
    elif primary_matches or any(x["status"] == "VERIFIED" for x in constraint_statuses): status = "PARTIALLY_SUPPORTED"
    else: status = "UNKNOWN"
    return {"primary_relation_status": "VERIFIED" if primary_matches else "CONTRADICTED" if primary_contradicted else "UNKNOWN", "constraint_statuses": constraint_statuses, "first_evidence_alignment": first_a, "second_evidence_alignment": second_a, "first_evidence_triples": ta, "second_evidence_triples": tb, "bridge_entity": bridge_entity or "", "bridge_entity_verified": bridge_verified, "argument_role_verified": bool(primary_matches), "direction_verified": bool(primary_matches), "relation_direction_verified": bool(primary_matches), "cross_source_verified": bool(bridge.get("source_identity_verified") and bridge.get("source_pair")), "cross_sentence_complementarity": complement, "matched_primary_relation_side": "+".join(primary_sides) if primary_sides else "NONE", "matched_constraint_sides": constraint_sides, "matched_evidence_spans": [x.get("evidence_span", "") for x in [first_a, second_a] if x.get("evidence_span")] + [x["span"] for x in constraint_sides], "rejection_reason": "" if status == "VERIFIED" else "PRIMARY_OR_CONSTRAINT_ROLE_DIRECTION_NOT_VERIFIED", "chain_relation_status": status, "matched_relation_side": "+".join(primary_sides) if primary_sides else "NONE", "matched_relation_span": " | ".join([x.get("evidence_span", "") for x in [first_a, second_a] if x.get("evidence_span")])}


