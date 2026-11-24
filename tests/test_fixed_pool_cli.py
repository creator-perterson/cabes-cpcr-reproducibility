"""Synthetic CLI checks using a local, generated tokenizer.json."""
from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tokenizers import Tokenizer, models, pre_tokenizers

REPO = Path(__file__).resolve().parents[1]
FIXTURE = runpy.run_path(str(REPO / "scripts" / "run_level2_smoke.py"))


class FixedPoolCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        tokenizer = Tokenizer(models.WordLevel({"[UNK]": 0, "Alpha": 1, "Beta": 2}, unk_token="[UNK]"))
        tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
        self.tokenizer_path = self.root / "tokenizer.json"
        tokenizer.save(str(self.tokenizer_path))
        self.tokenizer_hash = hashlib.sha256(self.tokenizer_path.read_bytes()).hexdigest()
        evidence, chains = FIXTURE["make_fixture"]()
        self.record = {
            "question_id": "synthetic-1",
            "question": "Alpha Beta",
            "evidence": evidence,
            "chains": chains,
            "relevance": {"u1": 1.0, "u2": 0.9},
            "demand": {},
            "candidate_universe_sha256": "synthetic-fixture",
        }
        self.input_path = self.root / "inputs.jsonl"
        self.input_path.write_text(json.dumps(self.record) + "\n", encoding="utf-8")
        self.output_path = self.root / "output.jsonl"

    def invoke(self, tokenizer_hash=None):
        return subprocess.run(
            [sys.executable, "-B", str(REPO / "scripts" / "run_fixed_pool.py"),
             "--input", str(self.input_path), "--tokenizer", str(self.tokenizer_path),
             "--tokenizer-sha256", tokenizer_hash or self.tokenizer_hash,
             "--config", str(REPO / "configs" / "r14_search.json"),
             "--output", str(self.output_path)],
            cwd=self.root, capture_output=True, text=True,
        )

    def test_synthetic_tokenizer_returns_four_distinct_cells(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in self.output_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["cell"] for row in rows], ["A00", "A01", "A10", "A11"])
        self.assertTrue(all(row["actual_context_tokens"] <= 256 for row in rows))

    def test_wrong_tokenizer_hash_does_not_create_output(self):
        result = self.invoke("0" * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output_path.exists())

    def test_duplicate_question_does_not_create_output(self):
        self.input_path.write_text((json.dumps(self.record) + "\n") * 2, encoding="utf-8")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output_path.exists())

    def test_existing_output_is_not_overwritten(self):
        self.output_path.write_text("keep", encoding="utf-8")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output_path.read_text(encoding="utf-8"), "keep")
