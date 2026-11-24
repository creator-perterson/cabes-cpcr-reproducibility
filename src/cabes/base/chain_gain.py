"""Set-valued ChainGain for v1.1/v1.2 with hard VERIFIED gating."""
from .score_chains_v0 import jaccard

def chain_reward_v12(chain):
    if chain.get("chain_relation_status") != "VERIFIED": return 0.0
    p = chain.get("score_v12_parts", chain.get("score_v11_parts", {}))
    return max(0.0, min(1.0, .30*p.get("first_hop_relevance", 0) + .25*p.get("bridge_quality", 0) + .25*p.get("relation_alignment", 0) + .20*p.get("cross_sentence_complementarity", 0) - .05*p.get("redundancy_penalty", 0)))

def chain_gain_for_set(uids, chains, version):
    selected = set(uids); eligible=[]
    for c in chains:
        if not set(c.get("uids", [])) <= selected: continue
        reward = chain_reward_v12(c) if version in {"v12", "v11"} else float(c.get("score_v0", 0))
        if reward > 0: eligible.append((reward, c))
    used_uids=set(); used_relations=set(); gain=0.0; chosen=[]
    for reward, c in sorted(eligible, key=lambda x: (-x[0], x[1]["chain_id"])):
        bridge = c.get("relation_alignment", {}).get("bridge_entity", "") or c.get("bridge", {}).get("bridge_key", "")
        relation_key = (c.get("relation_alignment", {}).get("primary_relation_status", ""), bridge)
        if set(c["uids"]) & used_uids or relation_key in used_relations: continue
        gain += reward / 2; used_uids.update(c["uids"]); used_relations.add(relation_key); chosen.append(c["chain_id"])
    return gain, chosen


