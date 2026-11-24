"""Create the bounded Level 1 snapshot from an external frozen metrics file.

This command is used during package assembly. It removes linkable question and
cluster hashes and keeps only the numeric fields needed by the offline
recomputation. It does not modify the input file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


KEEP_FIELDS = (
    "actual_context_tokens",
    "budget_violation",
    "evidence_selection_precision",
    "gold_document_coverage",
    "method",
    "question_type",
    "reader_em",
    "reader_f1",
    "search_wall_time_ms",
    "selector_latency_ms",
    "selector_status",
    "strict_complete",
    "supporting_fact_recall",
)


def load_rows(path: Path) -> list[dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document["rows"]
    if not isinstance(rows, list):
        raise ValueError("Input rows must be a list")
    return rows


def sanitize(rows: list[dict]) -> dict:
    question_keys = list(dict.fromkeys(row["question_key"] for row in rows))
    cluster_keys = list(dict.fromkeys(row["cluster_key"] for row in rows))
    question_index = {key: index for index, key in enumerate(question_keys)}
    cluster_index = {key: index for index, key in enumerate(cluster_keys)}

    sanitized_rows = []
    for row in rows:
        sanitized = {field: row.get(field) for field in KEEP_FIELDS}
        sanitized["question_index"] = question_index[row["question_key"]]
        sanitized["cluster_index"] = cluster_index[row["cluster_key"]]
        sanitized_rows.append(sanitized)

    return {
        "status": "SANITIZED_DERIVED_METRICS",
        "source_question_count": len(question_keys),
        "source_cluster_count": len(cluster_keys),
        "removed_fields": ["question_key", "cluster_key"],
        "ordering": "Original frozen row, question and first-seen cluster order preserved for statistical replay.",
        "rows": sanitized_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    raw = args.input.read_bytes()
    sanitized = sanitize(load_rows(args.input))
    sanitized["source_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sanitized, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "rows": len(sanitized["rows"]),
                "questions": sanitized["source_question_count"],
                "clusters": sanitized["source_cluster_count"],
                "source_sha256": sanitized["source_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
