"""Run a bounded synthetic smoke test for the copied CABES/CPCR modules."""
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.cpcr.proxy import compute_chain_coverage, validate_search_record  # noqa: E402
from src.cpcr.search import CPCRBlockSearch  # noqa: E402


class SimpleBudget:
    def __init__(self, evidence: list[dict], limit: int):
        self.evidence = {row["sentence_uid"]: row for row in evidence}
        self.limit = limit
        self.calls = 0
        self.hits = 0
        self.misses = 0
        self.token_time_ms = 0.0
        self.memo: dict[tuple[str, ...], dict] = {}

    def evaluate(self, uids: tuple[str, ...] | list[str]) -> dict:
        key = tuple(sorted(uids))
        if key in self.memo:
            self.hits += 1
            return self.memo[key]
        self.misses += 1
        self.calls += 1
        token_count = sum(len(self.evidence[uid]["sentence_text"].split()) for uid in key)
        result = {"uids": key, "tokens": token_count, "valid": token_count <= self.limit}
        self.memo[key] = result
        return result


def make_fixture() -> tuple[list[dict], list[dict]]:
    evidence = [
        {
            "sentence_uid": "u1",
            "document_id": "d1",
            "document_title": "Alpha",
            "sentence_text": "Alpha connects the bridge entity to Beta.",
            "retrieval_rank": 0,
            "original_document_row": 0,
            "original_sentence_index": 0,
        },
        {
            "sentence_uid": "u2",
            "document_id": "d2",
            "document_title": "Beta",
            "sentence_text": "Beta provides the second relation.",
            "retrieval_rank": 1,
            "original_document_row": 1,
            "original_sentence_index": 0,
        },
    ]
    chains = [
        {
            "chain_id": "chain-1",
            "uids": ["u1", "u2"],
            "bridge": {
                "source_identity_verified": True,
                "source_pair": ["d1", "d2"],
                "bridge_key": "Beta",
            },
            "relation_alignment": {
                "cross_source_verified": True,
                "chain_relation_status": "VERIFIED",
                "primary_relation_status": "VERIFIED",
                "bridge_entity": "Beta",
            },
            "score_v12_parts": {
                "first_hop_relevance": 1.0,
                "bridge_quality": 1.0,
                "relation_alignment": 1.0,
                "cross_sentence_complementarity": 1.0,
                "redundancy_penalty": 0.0,
            },
            "chain_relation_status": "VERIFIED",
        }
    ]
    return evidence, chains


def main() -> None:
    evidence, chains = make_fixture()
    validate_search_record(
        {
            "question_id": "synthetic-1",
            "evidence": evidence,
            "chains": chains,
            "demand": {},
            "gold_used_for_selection": False,
        }
    )
    coverage = compute_chain_coverage(["u1", "u2"], chains)
    budget = SimpleBudget(evidence, limit=64)
    config = {
        "beam_width": 2,
        "max_depth": 2,
        "max_path_atomic_edit_units": 2,
        "max_transition_attempts": 50,
        "max_unique_state_proposals": 50,
        "max_objective_evaluations": 50,
        "max_total_atomic_edit_units": 20,
        "sentence_cap": 8,
        "objective": {"alpha": 1.0, "beta": 0.4, "gamma": 0.1, "delta": 0.1},
    }
    search = CPCRBlockSearch(
        "Which entity connects Alpha and Beta?",
        evidence,
        chains,
        {"u1": 1.0, "u2": 0.9},
        budget,
        config,
        "S",
        [],
        cpcr_enabled=True,
    )
    result, _, cost, _ = search.run()
    output = {
        "status": "PASS",
        "proxy": {
            "available": coverage.available,
            "covered_chains": coverage.covered_chains,
            "total_chains": coverage.total_chains,
        },
        "selected_uids": list(result["selected_uids"]),
        "completeness_proxy": result.get("completeness_proxy"),
        "proxy_available": result.get("proxy_available"),
        "termination_reason": cost["termination_reason"],
        "formal_run_started": False,
    }
    output_path = REPO / "results" / "smoke" / "level2_smoke.json"
    output_path.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
