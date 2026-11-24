from __future__ import annotations

import json
import runpy
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(REPO / "scripts" / "recompute_level1.py"))


class Level1RecomputeTests(unittest.TestCase):
    def test_recomputed_summary_matches_expected(self):
        document = MODULE["load_document"](
            REPO / "results" / "level1" / "r14_per_question_metrics_sanitized.json"
        )
        actual = MODULE["recompute"](document)
        expected = json.loads(
            (REPO / "results" / "level1" / "expected_summary.json").read_text(encoding="utf-8")
        )
        self.assertEqual(actual["means"].keys(), expected["means"].keys())
        self.assertEqual(actual["paired_contrasts"]["n"], 1565)
        for method in expected["means"]:
            self.assertEqual(actual["means"][method]["n"], expected["means"][method]["n"])
            self.assertAlmostEqual(
                actual["means"][method]["strict_complete"],
                expected["means"][method]["strict_complete"],
                places=12,
            )
            self.assertAlmostEqual(
                actual["means"][method]["reader_f1"],
                expected["means"][method]["reader_f1"],
                places=12,
            )
        self.assertAlmostEqual(
            actual["paired_contrasts"]["A11_minus_A00"]["strict_complete"],
            expected["paired_contrasts"]["A11_minus_A00"]["strict_complete"],
            places=12,
        )
        self.assertAlmostEqual(
            actual["paired_contrasts"]["A11_minus_A00"]["reader_f1"],
            expected["paired_contrasts"]["A11_minus_A00"]["reader_f1"],
            places=12,
        )
