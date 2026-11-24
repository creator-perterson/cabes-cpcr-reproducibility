"""Guarded Level 3 preflight.

The command checks user-supplied paths and reports missing prerequisites. It
never starts a formal experiment.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--config", type=Path, default=Path("configs/level3_external_template.json"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config.get("formal_run_enabled") is True:
        raise SystemExit("Refusing to run a formal experiment from this bounded release candidate")

    paths = {
        key: value
        for key, value in config.items()
        if key.endswith("_root") and value is not None
    }
    checks = {key: {"configured": True, "exists": Path(value).exists()} for key, value in paths.items()}
    result = {
        "status": "PREFLIGHT_ONLY",
        "formal_run_started": False,
        "checks": checks,
        "required_authorization": config.get("historical_authorization"),
        "message": "Level 3 remains unverified and requires separately authorized assets and runtime identity.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
