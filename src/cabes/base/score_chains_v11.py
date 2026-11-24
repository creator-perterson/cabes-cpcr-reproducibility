"""CABES-v0.1.1 chain score: relation-aware and strictly gated."""
from __future__ import annotations
from .bridge_quality import content_tokens
from .score_chains_v0 import jaccard, sentence_relevance
from .chain_relation_alignment import align_query_relation_to_chain

def score_chain_v11(question, first, second, anchors, bridge, demand):
    alignment=align_query_relation_to_chain(question,demand,first,second,bridge)
    fa,fb=content_tokens(first.get("sentence_text","")),content_tokens(second.get("sentence_text","")); red=jaccard(fa,fb)
    first_rel=sentence_relevance(question,first,anchors); second_rel=sentence_relevance(question,second,anchors)
    bq=float(bridge.get("bridge_match_score",0)); comp=float(alignment.get("cross_sentence_complementarity",False)); rel=float(alignment.get("relation_direction_verified",False) and alignment.get("matched_relation_side")!="NONE")
    verified=float(alignment.get("chain_relation_status")=="VERIFIED")
    # Components are diagnostics only. ChainGain is computed separately and is
    # exactly zero for every non-VERIFIED chain.
    reward=max(0.0, .30*max(first_rel,second_rel)+.25*bq+.25*rel+.20*comp-.05*red) if verified else 0.0
    parts={"first_hop_relevance":max(first_rel,second_rel),"bridge_quality":bq,"relation_alignment":rel,"cross_sentence_complementarity":comp,"redundancy_penalty":red,"chain_relation_status":alignment["chain_relation_status"],"chain_reward":reward,"verified_chain":verified}
    return reward,parts,alignment


