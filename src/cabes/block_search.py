"""Fair sentence/block search used by the attribution experiment.

The objective is copied from the frozen v0.1.2 search contract.  Randomized
blocks affect only action generation; ChainGain always uses the original chain
graph.
"""
from __future__ import annotations
import hashlib, itertools, time
from pathlib import Path
from .base.bridge_quality import content_tokens  # noqa: E402
from .base.score_chains_v0 import jaccard  # noqa: E402
from .base.chain_gain import chain_gain_for_set  # noqa: E402

class BlockSearch:
    def __init__(self, question, evidence, chains, relevance, budget, cfg, method, blocks):
        self.question=question; self.pool={e["sentence_uid"]:e for e in evidence}; self.chains=chains; self.relevance=relevance; self.budget=budget; self.cfg=cfg; self.method=method; self.blocks=sorted({tuple(sorted(b["uids"])) for b in blocks})
        self.query=content_tokens(question); self.nodes=sorted(self.pool,key=lambda u:(-relevance.get(u,0),self.pool[u].get("retrieval_rank",99),u))[:cfg.get("sentence_cap",32)]
        self.objective_cache={}; self.state_costs={}; self.seen_states=set(); self.proposals=0; self.evaluations=0; self.attempted=0; self.duplicates=0; self.invalid=0; self.path_rejections=0; self.atomic_attempted=0; self.atomic_admitted=0; self.atomic_budget_rejections=0; self.block_scans=0; self.transitions=[]; self.anytime=[]; self.state_records=[]; self.start=time.perf_counter(); self.best=None; self.best_score=float("-inf"); self.stop_reason=None

    def _check_global_limits(self):
        if self.stop_reason is not None:
            return True
        if self.attempted >= self.cfg.get("max_transition_attempts", 2000):
            self.stop_reason = "MAX_TRANSITION_ATTEMPTS"
        elif self.proposals >= self.cfg.get("max_unique_state_proposals", 500):
            self.stop_reason = "MAX_UNIQUE_STATE_PROPOSALS"
        elif self.evaluations >= self.cfg.get("max_objective_evaluations", 500):
            self.stop_reason = "MAX_OBJECTIVE_EVALUATIONS"
        elif self.atomic_admitted >= self.cfg.get("max_total_atomic_edit_units", 500):
            self.stop_reason = "MAX_TOTAL_ATOMIC_EDIT_UNITS"
        return self.stop_reason is not None

    def _fallback_state(self):
        return {"selected_uids": (), "selected_chain_ids": [], "selected_blocks": [], "token_count": 0,
                "objective_score": 0.0, "components": {"Rel": 0.0, "ChainGain": 0.0, "Redundancy": 0.0, "Risk": 0.0, "chain_ids_rewarded": []},
                "action_history": [], "path_atomic_edit_units": 0, "state_hash": hashlib.sha256(b"()").hexdigest()}

    def complete(self,uids): return [c for c in self.chains if set(c.get("uids",[])) <= set(uids)]
    def objective(self,uids):
        key=tuple(sorted(set(uids)))
        if key in self.objective_cache: return self.objective_cache[key]
        fs=[content_tokens(self.pool[u].get("sentence_text","")) for u in key]
        coverage=len(self.query & (set().union(*fs) if fs else set()))/max(1,len(self.query)); rel=.7*coverage+.3*sum(sorted((self.relevance.get(u,0) for u in key),reverse=True)[:4])/4
        gain,chosen=chain_gain_for_set(key,self.chains,"v12"); pairs=list(itertools.combinations(fs,2)); red=max([jaccard(a,b) for a,b in pairs]+[0.]); risk=.05*sum(c.get("chain_relation_status") != "VERIFIED" for c in self.complete(key)); w=self.cfg.get("objective",{"alpha":1.0,"beta":.4,"gamma":.1,"delta":.1}); value=w["alpha"]*rel+w["beta"]*gain-w["gamma"]*red-w["delta"]*risk
        parts={"Rel":rel,"ChainGain":gain,"Redundancy":red,"Risk":risk,"chain_ids_rewarded":chosen}; self.objective_cache[key]=(value,parts); return value,parts

    def action(self, added, removed, typ, block=None):
        out={"type":typ,"added":sorted(added),"removed":sorted(removed),"atomic_edit_cost":len(added)+len(removed)}
        if block is not None: out["block_uids"]=list(block)
        return out

    def actions(self, state):
        selected=set(state["selected_uids"])
        for uid in self.nodes:
            if uid not in selected: yield selected|{uid},self.action([uid],[],"ADD_SENTENCE")
        for old in sorted(selected):
            for new in self.nodes:
                if new not in selected: yield (selected-{old})|{new},self.action([new],[old],"REPLACE_SENTENCE")
        if self.method in {"C-All","Random-Block"}:
            for block in self.blocks:
                self.block_scans += 1; target=set(block); added=target-selected
                if added: yield selected|target,self.action(added,[],"ADD_BLOCK",block)
                removed=selected-target
                if added or removed: yield target,self.action(added,removed,"REPLACE_WITH_BLOCK",block)

    def evaluate(self,uids,history,path):
        key=tuple(sorted(set(uids)))
        if key in self.seen_states:
            self.duplicates+=1
            return None
        if self._check_global_limits():
            return None
        self.seen_states.add(key)
        self.proposals+=1
        measured=self.budget.evaluate(key)
        if not measured["valid"]:
            self.invalid+=1
            return None
        if self._check_global_limits():
            return None
        value,parts=self.objective(key); self.evaluations+=1; self.state_costs[key]=path
        state={"selected_uids":key,"selected_chain_ids":[c["chain_id"] for c in self.complete(key)],"selected_blocks":[list(b) for b in self.blocks if set(b)<=set(key)],"token_count":measured["tokens"],"objective_score":value,"components":parts,"action_history":history,"path_atomic_edit_units":path,"state_hash":hashlib.sha256(repr(key).encode()).hexdigest()}
        self.state_records.append(state)
        if self.best is None or value > self.best_score or (value == self.best_score and key < self.best["selected_uids"]):
            self.best=state; self.best_score=value
        self.anytime.append({"objective_evaluation_index":self.evaluations,"transition_attempt_index":self.attempted,"atomic_edit_units_attempted":self.atomic_attempted,"atomic_edit_units_admitted":self.atomic_admitted,"tokenizer_calls":self.budget.calls,"elapsed_wall_time_ms":(time.perf_counter()-self.start)*1000,"current_state_hash":state["state_hash"],"current_objective":value,"best_so_far_state_hash":self.best["state_hash"],"best_so_far_objective":self.best_score,"best_so_far_tokens":self.best["token_count"],"best_so_far_uids":list(self.best["selected_uids"])})
        return state

    def propose(self,parent):
        max_path=self.cfg.get("max_path_atomic_edit_units",4); max_total=self.cfg.get("max_total_atomic_edit_units",500); max_trans=self.cfg.get("max_transition_attempts",2000)
        action_iterator=iter(self.actions(parent)); saw_atomic_rejection=False
        while self.stop_reason is None:
            if self._check_global_limits():
                return
            if self.attempted >= max_trans:
                self.stop_reason="MAX_TRANSITION_ATTEMPTS"
                return
            try:
                uids,action=next(action_iterator)
            except StopIteration:
                break
            self.attempted+=1; self.atomic_attempted+=action["atomic_edit_cost"]; self.transitions.append(action)
            next_path=parent["path_atomic_edit_units"]+action["atomic_edit_cost"]
            if next_path>max_path:
                self.path_rejections+=1
                continue
            if self.atomic_admitted+action["atomic_edit_cost"]>max_total:
                self.atomic_budget_rejections+=1; saw_atomic_rejection=True
                continue
            state=self.evaluate(uids,parent["action_history"]+[action],next_path)
            if state is not None:
                self.atomic_admitted+=action["atomic_edit_cost"]
                yield state
        if saw_atomic_rejection and self.stop_reason is None:
            self.stop_reason="MAX_TOTAL_ATOMIC_EDIT_UNITS"

    def run(self):
        empty=self.evaluate([],[],0); beam=[empty] if empty is not None else []; max_depth=self.cfg.get("max_depth",4); lookahead=self.method=="S-2Lookahead"; termination="MAX_DEPTH"
        for _ in range(max_depth):
            if self.stop_reason is not None:
                break
            terminals=[]
            for parent in beam:
                first=list(self.propose(parent))
                if self.stop_reason is not None:
                    break
                if not lookahead:
                    terminals.extend(first); continue
                for state in first:
                    if self.stop_reason is not None:
                        break
                    if state["path_atomic_edit_units"]-parent["path_atomic_edit_units"]>=2:
                        terminals.append(state); continue
                    second=list(self.propose(state))
                    terminals.extend(second or [state])
                    if self.stop_reason is not None:
                        break
                if self.stop_reason is not None:
                    break
            if self.stop_reason is not None:
                break
            if not terminals:
                self.stop_reason="NO_VALID_SUCCESSOR"
                break
            uniq={s["selected_uids"]:s for s in terminals}; beam=sorted(uniq.values(),key=lambda s:(-round(s["objective_score"],12),s["path_atomic_edit_units"],s["token_count"],s["selected_uids"]))[:self.cfg.get("beam_width",6)]
        if self.stop_reason is not None:
            termination=self.stop_reason
        result=self.best or empty or self._fallback_state(); wall=(time.perf_counter()-self.start)*1000
        cost={"attempted_transitions":self.attempted,"unique_state_proposals":self.proposals,"unique_state_evaluations":self.evaluations,"objective_evaluations":self.evaluations,"tokenizer_calls":self.budget.calls,"tokenizer_cache_hits":self.budget.hits,"tokenizer_cache_misses":self.budget.misses,"atomic_edit_units_attempted":self.atomic_attempted,"atomic_edit_units_admitted":self.atomic_admitted,"atomic_edit_unit_rejections":self.atomic_budget_rejections,"path_atomic_edit_units":result["path_atomic_edit_units"],"invalid_budget_states":self.invalid,"duplicate_states":self.duplicates,"token_budget_rejections":self.invalid,"path_cost_rejections":self.path_rejections,"candidate_block_scans":self.block_scans,"search_core_time_ms":max(0,wall-self.budget.token_time_ms),"tokenization_time_ms":self.budget.token_time_ms,"total_search_wall_time_ms":wall,"cpu_ms":wall,"termination_reason":termination,"selected_uid_count":len(result["selected_uids"]),"selected_block_count":len(result["selected_blocks"]),"final_tokens":result["token_count"]}
        return result,self.anytime,cost,self.state_records

