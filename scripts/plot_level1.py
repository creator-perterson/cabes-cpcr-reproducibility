"""Plot numeric R14 results after offline replay, with explicit exploratory scope."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--statistics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.statistics.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    methods = ["A00", "A01", "A10", "A11"]
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.6))
    for axis, metric, label in zip(axes, ["strict_complete", "reader_f1"], ["Strict completeness", "Reader F1"]):
        values = [result["means"][metric][method] for method in methods]
        axis.bar(methods, values, color=["#6b8393", "#da954d", "#659c90", "#365a74"])
        axis.set_ylabel(label)
        axis.set_ylim(0, 0.42)
        axis.spines[["right", "top"]].set_visible(False)
        for i, value in enumerate(values):
            axis.text(i, value + 0.008, f"{value:.4f}", ha="center", fontsize=8)
    fig.text(0.5, 0.02, "Offline replay of R14 frozen outcomes, 1,565 exposed questions", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(args.output_dir / "r14_clean_factorial_recomputed.png", dpi=200)
    fig.savefig(args.output_dir / "r14_clean_factorial_recomputed.pdf")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(8, 3.5))
    for axis, metric, label in zip(axes, ["strict_complete", "reader_f1"], ["Strict A11 minus A00", "Reader F1 A11 minus A00"]):
        entry = result["contrasts"]["A11-A00"][metric]
        for y, key, color in [(1, "paired_bootstrap_ci95", "#365a74"), (0, "cluster_bootstrap_ci95", "#bd6b45")]:
            low, high = entry[key]
            axis.hlines(y, low, high, color=color, linewidth=3)
            axis.scatter([entry["absolute_difference"]], [y], color=color, zorder=3)
        axis.axvline(0, color="#777777", linewidth=0.8)
        axis.set_yticks([0, 1], ["Cluster", "Question"])
        axis.set_ylim(-0.6, 1.6)
        axis.set_xlabel(label)
        axis.spines[["right", "top"]].set_visible(False)
    fig.text(0.5, 0.02, "Exploratory sensitivity, 10,000 draws, PCG64 seed 20261122", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(args.output_dir / "r14_sensitivity_recomputed.png", dpi=200)
    fig.savefig(args.output_dir / "r14_sensitivity_recomputed.pdf")
    plt.close(fig)
    print(json.dumps({"status": "PASS", "figure_count": 2, "matplotlib": matplotlib.__version__}))


if __name__ == "__main__":
    main()
