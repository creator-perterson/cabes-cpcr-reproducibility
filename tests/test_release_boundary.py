from __future__ import annotations

import unittest
import subprocess
import tempfile
from pathlib import Path

from scripts.scan_release_boundary import scan_history, should_fail


class ReleaseBoundaryGateTests(unittest.TestCase):
    def test_snapshot_findings_always_fail(self):
        result = {"snapshot": {"findings": [{"path": "README.md"}]}, "history": {"findings": []}}
        self.assertTrue(should_fail(result, fail_on_history=False))

    def test_history_findings_fail_in_release_gate_mode(self):
        result = {"snapshot": {"findings": []}, "history": {"findings": [{"object": "abc"}]}}
        self.assertTrue(should_fail(result, fail_on_history=True))

    def test_history_findings_are_reported_without_blocking_snapshot_only_mode(self):
        result = {"snapshot": {"findings": []}, "history": {"findings": [{"object": "abc"}]}}
        self.assertFalse(should_fail(result, fail_on_history=False))

    def test_deleted_binary_payload_remains_a_history_finding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)

            git("init")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            (root / "payload.pt").write_bytes(b"synthetic payload")
            git("add", "payload.pt")
            git("commit", "-m", "add fixture")
            git("rm", "payload.pt")
            git("commit", "-m", "remove fixture")
            findings = scan_history(root)["findings"]
            self.assertTrue(any("forbidden_payload_extension" in finding["findings"] for finding in findings))

    def test_identical_blob_under_multiple_historical_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)

            git("init")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            (root / "a.txt").write_bytes(b"shared fixture")
            (root / "z.pt").write_bytes(b"shared fixture")
            git("add", ".")
            git("commit", "-m", "add fixtures")
            git("rm", "z.pt")
            git("commit", "-m", "remove payload")
            findings = scan_history(root)["findings"]
            self.assertTrue(any("z.pt" in finding["paths"] for finding in findings))


if __name__ == "__main__":
    unittest.main()
