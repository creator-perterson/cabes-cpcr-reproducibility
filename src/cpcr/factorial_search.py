"""R14 fixed-candidate-pool search extracted from the frozen runner.

Class and run_one bodies retain the source AST. Paths and model loading are supplied externally.
"""
from __future__ import annotations
import hashlib
import time
from ..cabes.block_search import BlockSearch
from ..cabes.base.fair_budgeted_search import ExactBudget
from .proxy import compute_chain_coverage, validate_search_record
from .clean_factorial import choose_final, retain_beam

class FactorialSearch(BlockSearch):
    def __init__(self, *args, coverage_beam: bool, **kwargs):
        super().__init__(*args, **kwargs)
        self.coverage_beam = coverage_beam

    def evaluate(self, uids, history, path):
        state = super().evaluate(uids, history, path)
        if state is None:
            return None
        coverage = compute_chain_coverage(state["selected_uids"], self.chains)
        state["completeness_proxy"] = coverage.level
        state["proxy_available"] = coverage.available
        state["proxy_covered_chains"] = coverage.covered_chains
        state["proxy_total_chains"] = coverage.total_chains
        state["proxy_reason"] = coverage.reason
        if self.anytime:
            self.anytime[-1].update(
                completeness_proxy=coverage.level,
                proxy_available=coverage.available,
                proxy_covered_chains=coverage.covered_chains,
            )
        return state

    def run(self):
        empty = self.evaluate([], [], 0)
        beam = [empty] if empty is not None else []
        termination = "MAX_DEPTH"
        for _ in range(self.cfg.get("max_depth", 4)):
            if self.stop_reason is not None:
                break
            terminals = []
            for parent in beam:
                terminals.extend(self.propose(parent))
                if self.stop_reason is not None:
                    break
            if self.stop_reason is not None:
                break
            if not terminals:
                self.stop_reason = "NO_VALID_SUCCESSOR"
                break
            unique = {state["selected_uids"]: state for state in terminals}
            beam = retain_beam(list(unique.values()), self.cfg.get("beam_width", 6), self.coverage_beam)
        if self.stop_reason is not None:
            termination = self.stop_reason
        states = self.state_records or ([empty] if empty is not None else [])
        proxy_complete = bool(states) and all(state.get("proxy_available") is True for state in states)
        selected = choose_final(states, self.coverage_beam and proxy_complete)
        self.best = selected
        elapsed = (time.perf_counter() - self.start) * 1000
        cost = {
            "attempted_transitions": self.attempted,
            "unique_state_proposals": self.proposals,
            "objective_evaluations": self.evaluations,
            "tokenizer_calls": self.budget.calls,
            "atomic_edit_units_attempted": self.atomic_attempted,
            "atomic_edit_units_admitted": self.atomic_admitted,
            "path_atomic_edit_units": selected["path_atomic_edit_units"],
            "invalid_budget_states": self.invalid,
            "duplicate_states": self.duplicates,
            "path_cost_rejections": self.path_rejections,
            "total_search_wall_time_ms": elapsed,
            "tokenization_time_ms": self.budget.token_time_ms,
            "termination_reason": termination,
            "final_tokens": selected["token_count"],
            "proxy_available": proxy_complete,
        }
        return selected, self.anytime, cost, states

def run_one(record: dict, cfg: dict, tokenizer, coverage_beam: bool) -> tuple[dict, dict]:
    validate_search_record(record)
    budget = ExactBudget(record["evidence"], tokenizer, 256)
    blocks = [{"uids": chain["uids"]} for chain in record["chains"]]
    search = FactorialSearch(
        question=record["question"],
        evidence=record["evidence"],
        chains=record["chains"],
        relevance=record["relevance"],
        budget=budget,
        cfg=cfg,
        method="C-All",
        blocks=blocks,
        coverage_beam=coverage_beam,
    )
    _, trace, cost, states = search.run()
    final_choices = {
        "F0": choose_final(states, False),
        "F1": choose_final(states, True),
    }
    cells = []
    for final_rule, chosen in final_choices.items():
        measured = budget.evaluate(chosen["selected_uids"])
        if not measured["valid"] or measured["tokens"] > 256:
            raise RuntimeError(f"Budget violation for {record['question_id']}")
        cells.append({
            "question_id": record["question_id"],
            "cell": f"A{int(coverage_beam)}{int(final_rule == 'F1')}",
            "beam_rule": "B1" if coverage_beam else "B0",
            "final_rule": final_rule,
            "selected_uids": list(chosen["selected_uids"]),
            "context_sha256": hashlib.sha256(measured["context_text"].encode("utf-8")).hexdigest(),
            "actual_context_tokens": measured["tokens"],
            "objective_score": chosen["objective_score"],
            "objective_components": chosen["components"],
            "proxy_available": chosen.get("proxy_available", False),
            "completeness_proxy": chosen.get("completeness_proxy"),
            "proxy_reason": chosen.get("proxy_reason"),
            "search_cost": cost,
            "evaluated_state_count": len(states),
            "gold_used_for_selection": False,
            "candidate_universe_sha256": record["candidate_universe_sha256"],
        })
    trace_row = {
        "question_id": record["question_id"],
        "beam_rule": "B1" if coverage_beam else "B0",
        "trace_entries": len(trace),
        "states": states,
    }
    return cells, trace_row
