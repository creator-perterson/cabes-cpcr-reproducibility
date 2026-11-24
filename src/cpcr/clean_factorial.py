"""Selection rules for the clean CABES/CPCR factorial."""
from __future__ import annotations


def _uid(state: dict) -> tuple:
    value = state["selected_uids"]
    return tuple(value) if not isinstance(value, tuple) else value


def _proxy_available(state: dict) -> bool:
    return state.get("proxy_available") is True and state.get("completeness_proxy") is not None


def beam_key(state: dict, coverage_priority: bool) -> tuple:
    original = (
        -round(state["objective_score"], 12),
        state["path_atomic_edit_units"],
        state["token_count"],
        _uid(state),
    )
    if coverage_priority and _proxy_available(state):
        return (-int(state["completeness_proxy"]), *original)
    return original


def retain_beam(states: list[dict], width: int, coverage_priority: bool) -> list[dict]:
    if coverage_priority and states and all(_proxy_available(state) for state in states):
        return sorted(states, key=lambda state: beam_key(state, True))[:width]
    return sorted(states, key=lambda state: beam_key(state, False))[:width]


def final_key(state: dict, coverage_priority: bool) -> tuple:
    original = (-state["objective_score"], _uid(state))
    if coverage_priority and _proxy_available(state):
        return (-int(state["completeness_proxy"]), *original)
    return original


def choose_final(states: list[dict], coverage_priority: bool) -> dict:
    if not states:
        raise ValueError("Cannot select from an empty evaluated-state set")
    if coverage_priority and all(_proxy_available(state) for state in states):
        return min(states, key=lambda state: final_key(state, True))
    return min(states, key=lambda state: final_key(state, False))
