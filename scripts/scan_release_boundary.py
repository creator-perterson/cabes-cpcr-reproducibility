"""Scan the current snapshot and reachable Git history for release-boundary risks."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


FORBIDDEN_EXTENSIONS = {
    ".arrow", ".bin", ".ckpt", ".gguf", ".h5", ".hdf5", ".parquet", ".pkl",
    ".pickle", ".pt", ".pth", ".safetensors",
}
TEXT_EXTENSIONS = {
    "", ".cff", ".csv", ".gitignore", ".json", ".md", ".py", ".txt", ".toml", ".yaml", ".yml"
}


def text_findings(data: bytes) -> list[str]:
    text = data.decode("utf-8", errors="ignore")
    findings = []
    drive_path = re.compile(r"(?i)[a-z]:" + re.escape("\\"))
    credential_patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?:gh[pousr]|github_pat)_[A-Za-z0-9_]{20,}"),
        re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----"),
    ]
    if drive_path.search(text):
        findings.append("local_absolute_path")
    if any(pattern.search(text) for pattern in credential_patterns):
        findings.append("credential_pattern")
    return findings


def scan_snapshot(repo: Path) -> dict:
    findings = []
    files = [
        path for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
        and not ("results" in path.parts and "local" in path.parts)
    ]
    for path in files:
        relative = path.relative_to(repo)
        if path.suffix.lower() in FORBIDDEN_EXTENSIONS:
            findings.append({"path": relative.as_posix(), "findings": ["forbidden_payload_extension"]})
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if path.is_file():
            matches = text_findings(path.read_bytes())
            if matches:
                findings.append({"path": relative.as_posix(), "findings": matches})
    return {"snapshot_files": len(files), "findings": findings}


def scan_history(repo: Path) -> dict:
    objects = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--objects", "--all"], check=True, capture_output=True, text=True
    ).stdout.splitlines()
    commits = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--all"], check=True, capture_output=True, text=True
    ).stdout.splitlines()
    blobs = {}
    for commit in commits:
        tree = subprocess.run(
            ["git", "-C", str(repo), "ls-tree", "-r", "-z", commit], check=True, capture_output=True
        ).stdout
        for entry in tree.split(b"\0"):
            if not entry:
                continue
            metadata, path = entry.split(b"\t", 1)
            _, kind, object_id = metadata.decode("ascii").split()
            if kind == "blob":
                blobs.setdefault(object_id, set()).add(path.decode("utf-8", errors="surrogateescape"))
    findings = []
    blob_count = 0
    for object_id, blob_paths in blobs.items():
        paths = sorted(blob_paths)
        blob_count += 1
        if any(Path(path).suffix.lower() in FORBIDDEN_EXTENSIONS for path in paths):
            findings.append({"object": object_id, "paths": paths, "findings": ["forbidden_payload_extension"]})
        if not any(Path(path).suffix.lower() in TEXT_EXTENSIONS for path in paths):
            continue
        data = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-p", object_id], check=True, capture_output=True
        ).stdout
        matches = text_findings(data)
        if matches:
            findings.append({
                "object": object_id,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "paths": paths,
                "findings": matches,
            })
    return {"reachable_objects": len(objects), "blob_count": blob_count, "findings": findings}


def should_fail(result: dict, fail_on_history: bool) -> bool:
    return bool(result["snapshot"]["findings"] or (fail_on_history and result["history"]["findings"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--fail-on-history",
        action="store_true",
        help="fail when the current snapshot or reachable Git history contains findings",
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    result = {"snapshot": scan_snapshot(repo), "history": scan_history(repo)}
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if should_fail(result, args.fail_on_history):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
