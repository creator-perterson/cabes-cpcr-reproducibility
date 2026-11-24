"""Recompute bounded descriptive statistics from the sanitized Level 1 data."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def load_document(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("status") != "SANITIZED_DERIVED_METRICS":
        raise ValueError("Unexpected Level 1 status")
    return document


def recompute(document: dict) -> dict:
    rows = document["rows"]
    expected_methods = {"A00", "A01", "A10", "A11", "SetR"}
    identities = [(row["question_index"], row["method"]) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate question/method rows")
    questions = {row["question_index"] for row in rows}
    if len(questions) != document["source_question_count"]:
        raise ValueError("Question count mismatch")
    if len(rows) != len(questions) * len(expected_methods):
        raise ValueError("Incomplete method grid")
    for question in questions:
        if {row["method"] for row in rows if row["question_index"] == question} != expected_methods:
            raise ValueError("Method identity mismatch")
    if any(not math.isfinite(float(row[metric])) for row in rows for metric in ("strict_complete", "reader_f1")):
        raise ValueError("Non-finite metric")
    grouped: dict[str, list[dict]] = {}
    for row in document["rows"]:
        grouped.setdefault(row["method"], []).append(row)

    means = {}
    for method, rows in sorted(grouped.items()):
        means[method] = {
            "n": len(rows),
            "strict_complete": sum(float(row["strict_complete"]) for row in rows) / len(rows),
            "reader_f1": sum(float(row["reader_f1"]) for row in rows) / len(rows),
        }

    by_question: dict[int, dict[str, dict]] = {}
    for row in document["rows"]:
        by_question.setdefault(int(row["question_index"]), {})[row["method"]] = row
    pairs = [
        (methods["A11"], methods["A00"])
        for _, methods in sorted(by_question.items())
        if "A11" in methods and "A00" in methods
    ]
    paired = {
        "n": len(pairs),
        "A11_minus_A00": {
            "strict_complete": sum(
                float(a["strict_complete"]) - float(b["strict_complete"]) for a, b in pairs
            )
            / len(pairs),
            "reader_f1": sum(float(a["reader_f1"]) - float(b["reader_f1"]) for a, b in pairs)
            / len(pairs),
        },
    }
    return {"means": means, "paired_contrasts": paired}


def compare(actual: dict, expected: dict, tolerance: float) -> list[str]:
    errors = []
    if actual["paired_contrasts"]["n"] != expected["paired_contrasts"]["n"]:
        errors.append("Paired denominator mismatch")
    if actual["means"].keys() != expected["means"].keys():
        errors.append("Method set mismatch")
    for method, fields in expected["means"].items():
        for field, value in fields.items():
            observed = actual["means"].get(method, {}).get(field)
            if isinstance(value, (int, float)):
                if observed is None or abs(float(observed) - float(value)) > tolerance:
                    errors.append(f"means.{method}.{field}: {observed} != {value}")
            elif observed != value:
                errors.append(f"means.{method}.{field}: {observed} != {value}")
    for field, value in expected["paired_contrasts"]["A11_minus_A00"].items():
        observed = actual["paired_contrasts"]["A11_minus_A00"].get(field)
        if abs(float(observed) - float(value)) > tolerance:
            errors.append(f"paired.A11_minus_A00.{field}: {observed} != {value}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results/level1/r14_per_question_metrics_sanitized.json"),
    )
    parser.add_argument(
        "--expected",
        type=Path,
        default=Path("results/level1/expected_summary.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/level1/recomputed_summary.json"),
    )
    parser.add_argument("--tolerance", type=float, default=1e-12)
    args = parser.parse_args()

    actual = recompute(load_document(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(actual, indent=2, sort_keys=True), encoding="utf-8")
    expected = json.loads(args.expected.read_text(encoding="utf-8"))
    errors = compare(actual, expected, args.tolerance)
    if errors:
        raise SystemExit("Level 1 mismatch\n" + "\n".join(errors))
    print(json.dumps({"status": "PASS", "output": str(args.output), "methods": len(actual["means"])}))


if __name__ == "__main__":
    main()
