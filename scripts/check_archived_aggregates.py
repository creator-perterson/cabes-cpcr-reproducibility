"""Check saved C contrasts and SetR counts without running experiments."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def read_verified(path: Path, expected_sha256: str) -> dict:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest.lower() != expected_sha256.lower():
        raise ValueError(f"SHA-256 mismatch for {path.name}")
    return json.loads(data.decode("utf-8-sig"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--c-result", type=Path, required=True)
    parser.add_argument("--c-sha256", required=True)
    parser.add_argument("--c-config", type=Path, required=True)
    parser.add_argument("--c-config-sha256", required=True)
    parser.add_argument("--setr-receipt", type=Path, required=True)
    parser.add_argument("--setr-sha256", required=True)
    parser.add_argument("--r14-statistics", type=Path, required=True)
    parser.add_argument("--r14-sha256", required=True)
    args = parser.parse_args()

    result = read_verified(args.c_result, args.c_sha256)
    config = read_verified(args.c_config, args.c_config_sha256)
    receipt = read_verified(args.setr_receipt, args.setr_sha256)
    statistics = read_verified(args.r14_statistics, args.r14_sha256)
    errors = []
    rates = result["cell_rates"]
    for name, coefficients in config["contrasts"].items():
        value = sum(coefficient * rates[cell] for cell, coefficient in zip(config["cells"], coefficients))
        if abs(value - result["contrasts"][name]["estimate"]) > 1e-12:
            errors.append(f"C contrast mismatch: {name}")
    for key in ("seed", "draws", "bit_generator", "quantile_method", "rng_reset", "bootstrap"):
        if result["configuration"][key] != config[key]:
            errors.append(f"C configuration mismatch: {key}")
    counts = receipt["status_counts"]
    total = sum(counts.values())
    non_ok = total - counts.get("OK", 0)
    diagnostics = statistics["setr_selector_diagnostics"]
    if total != receipt["questions"] or total != diagnostics["n"]:
        errors.append("SetR denominator mismatch")
    if counts != diagnostics["status_counts"] or abs(non_ok / total - diagnostics["non_ok_rate"]) > 1e-12:
        errors.append("SetR status mismatch")
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "c_contrasts": len(config["contrasts"]),
                      "setr_questions": total, "setr_non_ok": non_ok, "errors": errors}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
