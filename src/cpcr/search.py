"""CPCR wrapper around the frozen CABES BlockSearch implementation.

Candidate generation, objective calculation, tokenizer accounting, and all
hard limits remain in the frozen implementation. This wrapper changes only
beam retention and final state selection when enabled.
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

from ..cabes.block_search import BlockSearch  # noqa: E402

from .proxy import compute_chain_coverage  # noqa: E402
from .state_selection import retain_states, select_final_state  # noqa: E402


class CPCRBlockSearch(BlockSearch):
    def cpcr_enabled_default():
        return False

    def __init__(self, *args, cpcr_enabled=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.cpcr_enabled = bool(cpcr_enabled)

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
                proxy_total_chains=coverage.total_chains,
            )
        return state

    def run(self):
        """Run the frozen search loop with only selection ordering replaced."""
        if not self.cpcr_enabled or not compute_chain_coverage([], self.chains).available:
            # Preserve the historical control byte-for-byte at the algorithm
            # boundary when CPCR is disabled or its proxy cannot be computed.
            return super().run()
        empty = self.evaluate([], [], 0)
        beam = [empty] if empty is not None else []
        max_depth = self.cfg.get("max_depth", 4)
        lookahead = self.method == "S-2Lookahead"
        termination = "MAX_DEPTH"
        for _ in range(max_depth):
            if self.stop_reason is not None:
                break
            terminals = []
            for parent in beam:
                first = list(self.propose(parent))
                if self.stop_reason is not None:
                    break
                if not lookahead:
                    terminals.extend(first)
                    continue
                for state in first:
                    if self.stop_reason is not None:
                        break
                    if state["path_atomic_edit_units"] - parent["path_atomic_edit_units"] >= 2:
                        terminals.append(state)
                        continue
                    second = list(self.propose(state))
                    terminals.extend(second or [state])
                    if self.stop_reason is not None:
                        break
                if self.stop_reason is not None:
                    break
            if self.stop_reason is not None:
                break
            if not terminals:
                self.stop_reason = "NO_VALID_SUCCESSOR"
                break
            unique = {state["selected_uids"]: state for state in terminals}
            beam = retain_states(list(unique.values()), self.cfg.get("beam_width", 6), self.cpcr_enabled)
        if self.stop_reason is not None:
            termination = self.stop_reason
        candidates = self.state_records or ([empty] if empty is not None else [])
        proxy_available = self.cpcr_enabled and bool(candidates) and all(
            state.get("proxy_available") is True for state in candidates
        )
        # When the proxy is unavailable, preserve the historical BlockSearch
        # self.best tie behavior exactly; only an available CPCR layer changes
        # final selection.
        result = select_final_state(candidates, True) if proxy_available else (self.best or empty or self._fallback_state())
        self.best = result
        wall = (time.perf_counter() - self.start) * 1000
        cost = {
            "attempted_transitions": self.attempted,
            "unique_state_proposals": self.proposals,
            "unique_state_evaluations": self.evaluations,
            "objective_evaluations": self.evaluations,
            "tokenizer_calls": self.budget.calls,
            "tokenizer_cache_hits": self.budget.hits,
            "tokenizer_cache_misses": self.budget.misses,
            "atomic_edit_units_attempted": self.atomic_attempted,
            "atomic_edit_units_admitted": self.atomic_admitted,
            "atomic_edit_unit_rejections": self.atomic_budget_rejections,
            "path_atomic_edit_units": result["path_atomic_edit_units"],
            "invalid_budget_states": self.invalid,
            "duplicate_states": self.duplicates,
            "token_budget_rejections": self.invalid,
            "path_cost_rejections": self.path_rejections,
            "candidate_block_scans": self.block_scans,
            "search_core_time_ms": max(0, wall - self.budget.token_time_ms),
            "tokenization_time_ms": self.budget.token_time_ms,
            "total_search_wall_time_ms": wall,
            "cpu_ms": wall,
            "termination_reason": termination,
            "selected_uid_count": len(result["selected_uids"]),
            "selected_block_count": len(result["selected_blocks"]),
            "final_tokens": result["token_count"],
            "cpcr_enabled": self.cpcr_enabled,
            "final_completeness_proxy": result.get("completeness_proxy"),
            "proxy_available": result.get("proxy_available", False),
        }
        return result, self.anytime, cost, self.state_records


