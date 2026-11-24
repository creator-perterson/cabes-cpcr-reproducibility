"""Selection keys shared by CPCR beam retention and final choice."""
from __future__ import annotations


def original_state_key(state: dict):
    return (
        -round(state["objective_score"], 12),
        state["path_atomic_edit_units"],
        state["token_count"],
        state["selected_uids"],
    )


def cpcr_state_key(state: dict):
    return (
        -int(state["completeness_proxy"]),
        *original_state_key(state),
    )


def _proxy_available(states: list[dict]) -> bool:
    return bool(states) and all(state.get("proxy_available") is True for state in states)


def retain_states(states: list[dict], width: int, enabled: bool) -> list[dict]:
    """Retain a beam using one proxy layer, with exact original fallback."""
    if not enabled or not _proxy_available(states):
        ordered = sorted(states, key=original_state_key)
    else:
        ordered = sorted(states, key=cpcr_state_key)
    return ordered[:width]


def select_final_state(states: list[dict], enabled: bool) -> dict:
    if not states:
        raise ValueError("Cannot select from an empty state collection")
    if enabled and _proxy_available(states):
        return min(states, key=cpcr_state_key)
    return min(states, key=original_state_key)
