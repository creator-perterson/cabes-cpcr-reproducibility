"""Level 2 R14 runner for externally supplied fixed search inputs and tokenizer."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.cpcr.factorial_search import run_one
from src.cpcr.proxy import validate_search_record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--tokenizer-sha256", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from tokenizers import Tokenizer

    digest = hashlib.sha256(args.tokenizer.read_bytes()).hexdigest()
    if digest != args.tokenizer_sha256:
        raise ValueError("Tokenizer hash mismatch")
    if args.output.exists():
        raise FileExistsError(args.output)
    engine = Tokenizer.from_file(str(args.tokenizer))

    def tokenizer(text, add_special_tokens=False):
        return {"input_ids": engine.encode(text, add_special_tokens=add_special_tokens).ids}

    config = json.loads(args.config.read_text(encoding="utf-8"))
    records = [json.loads(line) for line in args.input.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if not records or len({row["question_id"] for row in records}) != len(records):
        raise ValueError("Input must contain unique questions")
    for record in records:
        validate_search_record(record)
    output = []
    for record in records:
        for coverage_beam in (False, True):
            cells, _ = run_one(record, config, tokenizer, coverage_beam)
            output.extend(cells)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        for row in output:
            stream.write(json.dumps(row) + "\n")
    print(json.dumps({"questions": len(records), "cells": len(output), "reader_executed": False, "tokenizer_sha256": digest}))


if __name__ == "__main__":
    main()
