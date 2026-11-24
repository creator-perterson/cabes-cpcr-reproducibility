"""Frozen R14 statistics function extracted for saved-outcome replay.

Source provenance is recorded in the R1 mapping. No evaluator or Reader is imported.
"""
from __future__ import annotations

import collections
from collections import defaultdict
import numpy as np
from scipy.stats import binomtest

METHODS = ("A00", "A01", "A10", "A11", "SetR")
METRICS = ("strict_complete", "supporting_fact_recall", "reader_em", "reader_f1", "evidence_selection_precision", "gold_document_coverage", "actual_context_tokens")
CONTRASTS = {
    "A11-A00": {"A11": 1, "A00": -1},
    "A01-A00": {"A01": 1, "A00": -1},
    "A10-A00": {"A10": 1, "A00": -1},
    "A11-A01": {"A11": 1, "A01": -1},
    "A11-A10": {"A11": 1, "A10": -1},
    "SetR-A00": {"SetR": 1, "A00": -1},
    "SetR-A11": {"SetR": 1, "A11": -1},
    "beam_average": {"A10": 0.5, "A11": 0.5, "A00": -0.5, "A01": -0.5},
    "final_average": {"A01": 0.5, "A11": 0.5, "A00": -0.5, "A10": -0.5},
    "interaction": {"A11": 1, "A01": -1, "A10": -1, "A00": 1},
}
SEED = 20261122
DRAWS = 10000

def statistics(rows: list[dict]) -> dict:
    qids = list(dict.fromkeys(row["question_id"] for row in rows))
    index = {(row["question_id"], row["method"]): row for row in rows}
    groups = defaultdict(list)
    for i, qid in enumerate(qids):
        groups[index[qid, "A00"]["cluster"]].append(i)
    cluster_indices = list(groups.values())
    if len(cluster_indices) != 218 or max(map(len, cluster_indices)) != 1248:
        raise RuntimeError("Cluster cardinalities mismatch")
    rng = np.random.default_rng(SEED)
    cluster_draws = rng.integers(0, len(cluster_indices), size=(DRAWS, len(cluster_indices)))
    result = {
        "status": "EXPLORATORY_PAIRED_ANALYSIS",
        "questions": len(qids),
        "clusters": len(cluster_indices),
        "largest_cluster": max(map(len, cluster_indices)),
        "bootstrap_draws": DRAWS,
        "seed": SEED,
        "means": {},
        "contrasts": {},
        "cluster_bootstrap_weighting": "resample clusters and compute question-weighted mean",
        "empty_selection_precision": "undefined; precision means and paired contrasts use available values and report effective n",
        "cost_interpretation": "A00 and A01 share the B0 search trajectory; A10 and A11 share B1. SetR latency covers selector generation and packing. These costs are not additive per cell.",
        "costs": {},
    }
    for method in METHODS:
        method_rows = [row for row in rows if row["method"] == method]
        times = [row["search_wall_time_ms"] for row in method_rows if row["search_wall_time_ms"] is not None]
        selector_times = [row["selector_latency_ms"] for row in method_rows if row["selector_latency_ms"] is not None]
        result["costs"][method] = {
            "n": len(method_rows),
            "mean_search_wall_time_ms": float(np.mean(times)) if times else None,
            "mean_setr_selector_latency_ms": float(np.mean(selector_times)) if selector_times else None,
            "budget_violation_rate": float(np.mean([row["budget_violation"] for row in method_rows])),
            "selector_status_counts": dict(collections.Counter(row["selector_status"] for row in method_rows)),
        }
    for metric in METRICS:
        values = {method: np.array([index[qid, method][metric] if index[qid, method][metric] is not None else np.nan
                                    for qid in qids], dtype=float) for method in METHODS}
        result["means"][metric] = {method: float(np.nanmean(value)) for method, value in values.items()}
        result.setdefault("mean_effective_n", {})[metric] = {method: int(np.isfinite(value).sum()) for method, value in values.items()}
        for contrast, coefficients in CONTRASTS.items():
            difference = sum(coefficient * values[method] for method, coefficient in coefficients.items())
            valid = difference[np.isfinite(difference)]
            if not len(valid):
                raise RuntimeError(f"No valid paired observations for {contrast} {metric}")
            question_draws = rng.integers(0, len(valid), size=(DRAWS, len(valid)))
            cluster_sums = np.array([np.nansum(difference[group]) for group in cluster_indices])
            cluster_sizes = np.array([np.isfinite(difference[group]).sum() for group in cluster_indices])
            numerator = cluster_sums[cluster_draws].sum(axis=1)
            denominator = cluster_sizes[cluster_draws].sum(axis=1)
            sample = numerator[denominator > 0] / denominator[denominator > 0]
            loco = [(valid.sum() - cluster_sums[i]) / (len(valid) - cluster_sizes[i])
                    if len(valid) > cluster_sizes[i] else np.nan for i in range(len(cluster_indices))]
            entry = {
                "n": len(valid),
                "absolute_difference": float(valid.mean()),
                "paired_bootstrap_ci95": np.quantile(valid[question_draws].mean(axis=1), [0.025, 0.975]).tolist(),
                "cluster_bootstrap_ci95": np.quantile(sample, [0.025, 0.975]).tolist(),
                "loco_min": float(np.nanmin(loco)),
                "loco_max": float(np.nanmax(loco)),
                "loco_largest_cluster": float(loco[int(np.argmax([len(group) for group in cluster_indices]))]),
            }
            if len(coefficients) == 2:
                positive = next(method for method, weight in coefficients.items() if weight == 1)
                negative = next(method for method, weight in coefficients.items() if weight == -1)
                paired_mask = np.isfinite(difference)
                baseline = float(values[negative][paired_mask].mean())
                entry.update(treatment_mean=float(values[positive][paired_mask].mean()), control_mean=baseline,
                             relative_difference=float(valid.mean() / baseline) if baseline else None)
                if metric in ("strict_complete", "reader_em"):
                    favorable = int(((values[positive] == 1) & (values[negative] == 0)).sum())
                    unfavorable = int(((values[positive] == 0) & (values[negative] == 1)).sum())
                    entry["mcnemar_exact"] = {"favorable": favorable, "unfavorable": unfavorable,
                                              "p_value": float(binomtest(favorable, favorable + unfavorable, 0.5).pvalue) if favorable + unfavorable else 1.0}
            result["contrasts"].setdefault(contrast, {})[metric] = entry
    return result
