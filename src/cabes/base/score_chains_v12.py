"""CABES-v0.1.2 verified-chain score with primary/constraint gating."""
from .score_chains_v0 import jaccard, sentence_relevance
from .bridge_quality import content_tokens
from .chain_relation_alignment import align_query_relation_to_chain

def score_chain_v12(question, first, second, anchors, bridge, demand):
    alignment = align_query_relation_to_chain(question, demand, first, second, bridge)
    fa, fb = content_tokens(first.get("sentence_text", "")), content_tokens(second.get("sentence_text", ""))
    red = jaccard(fa, fb); first_rel = sentence_relevance(question, first, anchors); second_rel = sentence_relevance(question, second, anchors)
    verified = alignment.get("chain_relation_status") == "VERIFIED"
    reward = max(0.0, .30 * max(first_rel, second_rel) + .25 * float(bridge.get("bridge_match_score", 0)) + .25 * float(alignment.get("direction_verified", False)) + .20 * float(alignment.get("cross_sentence_complementarity", False)) - .05 * red) if verified else 0.0
    parts = {"first_hop_relevance": max(first_rel, second_rel), "bridge_quality": float(bridge.get("bridge_match_score", 0)), "relation_alignment": float(alignment.get("direction_verified", False)), "cross_sentence_complementarity": float(alignment.get("cross_sentence_complementarity", False)), "redundancy_penalty": red, "chain_relation_status": alignment.get("chain_relation_status"), "chain_reward": reward, "verified_chain": float(verified), "primary_relation_status": alignment.get("primary_relation_status"), "constraint_statuses": alignment.get("constraint_statuses", [])}
    return reward, parts, alignment


