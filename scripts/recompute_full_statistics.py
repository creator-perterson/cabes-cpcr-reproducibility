"""Replay frozen R14 statistics using saved numeric outcomes only."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def differences(actual, expected, location="root"):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            return [location + " keys differ"]
        return [error for key in expected for error in differences(actual[key], expected[key], location + "." + key)]
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return [location + " length differs"]
        return [error for index, value in enumerate(expected) for error in differences(actual[index], value, location + f"[{index}]")]
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or not math.isclose(actual, expected, abs_tol=1e-12, rel_tol=1e-12):
            return [f"{location} differs"]
        return []
    return [] if actual == expected else [location + " differs"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=REPO / "results/local/full_statistics")
    args = parser.parse_args()
    source = REPO / "results/level1/r14_per_question_metrics_sanitized.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    rows = [{**row, "question_id": row["question_index"], "cluster": row["cluster_index"]} for row in document["rows"]]
    from src.evaluation.r14_statistics import statistics

    result = statistics(rows)
    expected = json.loads((REPO / "results/level1/expected_full_statistics.json").read_text(encoding="utf-8"))
    errors = differences(result, expected)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "statistics.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    verification = {"status": "PASS" if not errors else "FAIL", "mismatches": errors, "metric_count": len(result["means"]), "contrast_count": len(result["contrasts"]), "draws": result["bootstrap_draws"], "questions": result["questions"], "source": str(source.name)}
    (args.output_dir / "verification.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    with (args.output_dir / "metric_table.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["method", "metric", "mean", "effective_n"])
        for metric, methods in result["means"].items():
            for method, value in methods.items():
                writer.writerow([method, metric, value, result["mean_effective_n"][metric][method]])
    with (args.output_dir / "contrast_table.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["contrast", "metric", "difference", "question_low", "question_high", "cluster_low", "cluster_high", "n"])
        for contrast, metrics in result["contrasts"].items():
            for metric, entry in metrics.items():
                writer.writerow([contrast, metric, entry["absolute_difference"], *entry["paired_bootstrap_ci95"], *entry["cluster_bootstrap_ci95"], entry["n"]])
    print(json.dumps(verification, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
