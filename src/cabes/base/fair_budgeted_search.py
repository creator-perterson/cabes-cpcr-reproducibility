"""Fair deterministic search with gated chain actions and path-cost accounting."""
from __future__ import annotations
import hashlib, itertools, time
from .bridge_quality import content_tokens, discover_structural_bridges
from .score_chains_v0 import jaccard, sentence_relevance, score_chain_v0
from .score_chains_v11 import score_chain_v11
from .score_chains_v12 import score_chain_v12
from .chain_gain import chain_gain_for_set

def serialize_context(evidence):
    ordered = sorted(evidence, key=lambda e:(e.get("retrieval_rank",0), e.get("original_document_row",0), e.get("original_sentence_index",0), e["sentence_uid"]))
    return "\n".join(f"[D{e.get('original_document_row',e.get('document_id'))}:S{e.get('original_sentence_index',0)}] {e.get('document_title','')}: {e.get('sentence_text','')}" for e in ordered)

class WordTokenizer:
    def __call__(self, text, add_special_tokens=False): return {"input_ids": text.split()}

class ExactBudget:
    def __init__(self, evidence, tokenizer=None, budget=256):
        self.pool={e["sentence_uid"]:e for e in evidence}; self.tokenizer=tokenizer or WordTokenizer(); self.budget=budget; self.memo={}; self.calls=0; self.hits=0; self.misses=0; self.token_time_ms=0.0
    def evaluate(self, uids):
        key=tuple(sorted(set(uids)))
        if not set(key) <= set(self.pool): raise ValueError("INVALID_SOURCE_UID")
        if key in self.memo: self.hits+=1; return self.memo[key]
        started=time.perf_counter(); text=serialize_context([self.pool[u] for u in key]); n=len(self.tokenizer(text, add_special_tokens=False)["input_ids"]); self.token_time_ms+=(time.perf_counter()-started)*1000; self.calls+=1; self.misses+=1
        self.memo[key]={"uids":key,"context_text":text,"tokens":n,"valid":n<=self.budget}; return self.memo[key]

def candidate_universe(question, evidence, anchors, demand=None, cfg=None):
    cfg=cfg or {}; demand=demand if isinstance(demand,dict) else {}; pool={e["sentence_uid"]:e for e in evidence}
    relevance={u:sentence_relevance(question,e,anchors) for u,e in pool.items()}; anchor_uids=set(sorted(pool,key=lambda u:(-relevance[u], pool[u].get("retrieval_rank",99),u))[:cfg.get("anchor_cap",16)])
    edges=discover_structural_bridges(evidence, anchor_uids=anchor_uids); chains=[]
    for edge in edges:
        a,b=pool[edge["anchor_evidence"]],pool[edge["target_evidence"]]; cid="C"+hashlib.sha256(f"{a['sentence_uid']}|{b['sentence_uid']}|{edge['bridge_key']}".encode()).hexdigest()[:16]
        v0,v0p=score_chain_v0(question,a,b,anchors,{**edge,"bridge_confidence":edge.get("bridge_match_score",.85)}); v11,v11p,_=score_chain_v11(question,a,b,anchors,edge,demand); v12,v12p,alignment=score_chain_v12(question,a,b,anchors,edge,demand)
        chains.append({"chain_id":cid,"uids":[a["sentence_uid"],b["sentence_uid"]],"edge_id":cid[1:],"bridge":edge,"score_v0":v0,"score_v0_parts":v0p,"score_v11":v11,"score_v11_parts":v11p,"score_v12":v12,"score_v12_parts":v12p,"relation_alignment":alignment,"chain_relation_status":alignment["chain_relation_status"]})
    chains.sort(key=lambda c:(c["uids"], c["chain_id"])); signature="\n".join(f"{c['chain_id']}|{','.join(c['uids'])}" for c in chains); uh=hashlib.sha256(signature.encode()).hexdigest()
    return chains, relevance, {"edges":edges,"candidate_universe_sha256":uh,"anchor_uids":sorted(anchor_uids)}

class FairSearch:
    def __init__(self, question, evidence, chains, relevance, budget, cfg, score_version="v12", action_mode="S", demand=None):
        self.question=question; self.pool={e["sentence_uid"]:e for e in evidence}; self.chains=chains; self.relevance=relevance; self.budget=budget; self.cfg=cfg; self.score_version=score_version; self.action_mode=action_mode; self.demand=demand or {}
        self.query=content_tokens(question); self.nodes=sorted(self.pool,key=lambda u:(-relevance.get(u,0),self.pool[u].get("retrieval_rank",99),u))[:cfg.get("sentence_cap",32)]
        self.unique=0; self.proposals=0; self.attempted=0; self.duplicates=0; self.invalid=0; self.path_rejections=0; self.atomic_units=0; self.atomic_attempted_units=0; self.objective_evals=0; self.bridge_evals=0; self.relation_evals=0; self.cap_hit=False; self.attempt_cap=False; self.states={}; self.state_costs={}; self.objective_cache={}; self.transitions=[]; self.start=time.perf_counter()
    def complete(self,uids): return [c for c in self.chains if set(c["uids"]) <= set(uids)]
    def objective(self,uids):
        key=tuple(sorted(set(uids)))
        if key in self.objective_cache: return self.objective_cache[key]
        fs=[content_tokens(self.pool[u].get("sentence_text", "")) for u in key]; coverage=len(self.query & (set().union(*fs) if fs else set()))/max(1,len(self.query)); rel=.7*coverage+.3*sum(sorted((self.relevance.get(u,0) for u in key), reverse=True)[:4])/4
        self.bridge_evals+=len(self.chains); self.relation_evals+=len(self.complete(key)); gain,chosen=chain_gain_for_set(key,self.chains,self.score_version); pairs=list(itertools.combinations(fs,2)); red=max([jaccard(a,b) for a,b in pairs]+[0.]); risk=.05*sum(c.get("chain_relation_status") != "VERIFIED" for c in self.complete(key)); w=self.cfg.get("objective",{"alpha":1.0,"beta":.4,"gamma":.1,"delta":.1}); value=w["alpha"]*rel+w["beta"]*gain-w["gamma"]*red-w["delta"]*risk
        self.objective_evals+=1; self.objective_cache[key]=(value,{"Rel":rel,"ChainGain":gain,"Redundancy":red,"Risk":risk,"chain_ids_rewarded":chosen}); return self.objective_cache[key]
    def _action(self, added, removed, typ, **extra):
        a={"type":typ,"added":sorted(added),"removed":sorted(removed),"atomic_edit_cost":len(added)+len(removed)}; a.update(extra); return a
    def actions(self, state):
        us=set(state["selected_uids"])
        for u in self.nodes:
            if u not in us: yield us|{u}, self._action([u],[],"ADD_SENTENCE")
        for old in sorted(us):
            for new in self.nodes:
                if new not in us: yield (us-{old})|{new}, self._action([new],[old],"REPLACE_SENTENCE")
        if self.action_mode in {"C-All","C-Verified"}:
            for c in self.chains:
                if self.action_mode == "C-Verified" and c.get("chain_relation_status") != "VERIFIED": continue
                target=set(c["uids"]); added=target-us
                if added: yield us|target, self._action(added,[],"ADD_CHAIN",chain_id=c["chain_id"])
                added=target-us; removed=us-target
                if added or removed: yield target, self._action(added,removed,"REPLACE_WITH_CHAIN",chain_id=c["chain_id"])
    def _evaluate(self, uids, history, path_cost):
        key=tuple(sorted(set(uids))); previous=self.state_costs.get(key)
        if previous is not None and path_cost >= previous: self.duplicates+=1; return None
        if self.proposals >= self.cfg.get("max_unique_state_proposals", self.cfg.get("max_unique_state_evaluations",500)): self.cap_hit=True; return None
        self.proposals+=1; m=self.budget.evaluate(key)
        if not m["valid"]: self.invalid+=1; return None
        value,parts=self.objective(key); self.unique+=1; self.state_costs[key]=path_cost; result={"selected_uids":key,"selected_chain_ids":[c["chain_id"] for c in self.complete(key)],"token_count":m["tokens"],"objective_score":value,"components":parts,"action_history":history,"path_atomic_edit_units":path_cost,"state_hash":hashlib.sha256(repr(key).encode()).hexdigest()}; self.states[key]=result; return result
    def run(self):
        empty=self._evaluate([],[],0); beam=[empty] if empty else []; trace=[]; termination="MAX_DEPTH"; max_path=self.cfg.get("max_path_atomic_edit_units",4)
        max_total=self.cfg.get("max_total_atomic_edit_units", self.cfg.get("max_atomic_uid_edit_units",500))
        for depth in range(self.cfg.get("max_depth",4)):
            candidates={s["selected_uids"]:s for s in beam}; level=[]
            for parent in beam:
                for uids,action in self.actions(parent):
                    self.attempted+=1; self.atomic_attempted_units+=action["atomic_edit_cost"]; self.transitions.append(action); next_cost=parent["path_atomic_edit_units"]+action["atomic_edit_cost"]
                    if self.attempted > self.cfg.get("max_transition_attempts",2000): self.attempt_cap=True; termination="MAX_TRANSITION_ATTEMPTS"; break
                    if self.atomic_units+action["atomic_edit_cost"] > max_total: self.cap_hit=True; termination="MAX_TOTAL_ATOMIC_EDIT_UNITS"; break
                    if next_cost > max_path: self.path_rejections+=1; level.append({"child":list(sorted(uids)),"action":action,"valid":False,"reason":"PATH_COST"}); continue
                    self.atomic_units+=action["atomic_edit_cost"]; key=tuple(sorted(uids))
                    if key in candidates and next_cost >= candidates[key]["path_atomic_edit_units"]: self.duplicates+=1; level.append({"child":list(key),"action":action,"valid":False,"reason":"DUPLICATE_STATE"}); continue
                    child=self._evaluate(key,parent["action_history"]+[action],next_cost); level.append({"child":list(key),"action":action,"valid":child is not None,"path_atomic_edit_units":next_cost});
                    if child is not None: candidates[key]=child
                if self.cap_hit or self.attempt_cap: break
            if not candidates: termination="NO_VALID_SUCCESSOR"; break
            beam=sorted(candidates.values(),key=lambda s:(-round(s["objective_score"],12),s["path_atomic_edit_units"],s["token_count"],s["selected_uids"]))[:self.cfg.get("beam_width",6)]; trace.append({"depth":depth+1,"expanded":len(level),"beam":[{"uids":list(s["selected_uids"]),"score":s["objective_score"],"tokens":s["token_count"],"path_atomic_edit_units":s["path_atomic_edit_units"]} for s in beam],"transitions":level})
            if self.cap_hit or self.attempt_cap: break
        result=beam[0] if beam else {"selected_uids":(),"selected_chain_ids":[],"token_count":0,"objective_score":0.0,"components":{"Rel":0.0,"ChainGain":0.0,"Redundancy":0.0,"Risk":0.0},"action_history":[],"path_atomic_edit_units":0}; wall=(time.perf_counter()-self.start)*1000
        return result,trace,{"attempted_transitions":self.attempted,"unique_state_proposals":self.proposals,"unique_state_evaluations":self.unique,"unique_successors":self.unique,"valid_scored_states":self.unique,"invalid_budget_states":self.invalid,"token_budget_rejections":self.invalid,"path_cost_rejections":self.path_rejections,"duplicate_states":self.duplicates,"atomic_uid_edit_units":self.atomic_units,"attempted_atomic_uid_edit_units":self.atomic_attempted_units,"tokenizer_cache_hits":self.budget.hits,"tokenizer_cache_misses":self.budget.misses,"tokenizer_calls":self.budget.calls,"tokenization_time_ms":self.budget.token_time_ms,"objective_evaluations":self.objective_evals,"bridge_evaluations":self.bridge_evals,"relation_evaluations":self.relation_evals,"search_wall_time_ms":wall,"cpu_ms":wall,"cap_hit":self.cap_hit or self.attempt_cap,"evaluation_cap_hit":self.cap_hit,"termination_reason":termination,"selected_uid_count":len(result["selected_uids"]),"selected_chain_count":len(result["selected_chain_ids"]),"final_tokens":result["token_count"],"path_atomic_edit_units":result["path_atomic_edit_units"],"search_core_time_ms":max(0.,wall-self.budget.token_time_ms)}


