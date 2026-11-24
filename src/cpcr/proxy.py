"""One deterministic, inference-time structural chain coverage proxy.

This module accepts only label-free search inputs. It intentionally does not
import or inspect Train annotations, answers, Reader outputs, or Validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ChainCoverage:
    available: bool
    level: int | None
    covered_chains: int
    total_chains: int
    reason: str


def _valid_chain(chain: dict) -> bool:
    uids = chain.get("uids")
    bridge = chain.get("bridge")
    alignment = chain.get("relation_alignment")
    return (
        isinstance(uids, list)
        and len(uids) >= 2
        and len(set(uids)) == len(uids)
        and isinstance(bridge, dict)
        and bridge.get("source_identity_verified") is True
        and isinstance(bridge.get("source_pair"), list)
        and len(bridge["source_pair"]) >= 2
        and isinstance(alignment, dict)
        and alignment.get("cross_source_verified") is True
    )


def compute_chain_coverage(selected_uids: Iterable[str], chains: list[dict]) -> ChainCoverage:
    """Return the count of structurally valid chains fully contained in a state.

    The proxy layer is a count, not a new weighted score. A missing or invalid
    chain schema makes the proxy unavailable so the caller can use CABES's
    original Objective-first ordering.
    """
    if not isinstance(chains, list) or not chains:
        return ChainCoverage(False, None, 0, 0, "NO_CHAIN_UNIVERSE")
    valid_chains = [chain for chain in chains if isinstance(chain, dict) and _valid_chain(chain)]
    if not valid_chains:
        return ChainCoverage(False, None, 0, 0, "INVALID_CHAIN_SCHEMA")
    selected = set(selected_uids)
    total = len(valid_chains)
    covered = sum(set(chain["uids"]).issubset(selected) for chain in valid_chains)
    return ChainCoverage(True, covered, covered, total, "STRUCTURAL_CHAIN_COVERAGE")


def validate_search_record(record: dict) -> None:
    """Reject label-bearing fields at the algorithm boundary."""
    if not isinstance(record, dict):
        raise ValueError("Search record must be a mapping")
    forbidden = {"facts", "gold_passages", "answer", "reader_metrics", "predictions"}
    present = forbidden.intersection(record)
    if present:
        raise ValueError(f"Gold/Reader fields are forbidden in CPCR search input: {sorted(present)}")
    if record.get("gold_used_for_selection", False) is not False:
        raise ValueError("Gold selection flag must be false")
    for required in ("question_id", "evidence", "chains", "demand"):
        if required not in record:
            raise ValueError(f"Missing label-free search field: {required}")
