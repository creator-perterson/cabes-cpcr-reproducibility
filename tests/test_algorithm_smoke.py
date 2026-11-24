from __future__ import annotations

import runpy
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SMOKE = runpy.run_path(str(REPO / "scripts" / "run_level2_smoke.py"))


class AlgorithmSmokeTests(unittest.TestCase):
    def test_structural_proxy_counts_complete_chain(self):
        evidence, chains = SMOKE["make_fixture"]()
        coverage = SMOKE["compute_chain_coverage"](["u1", "u2"], chains)
        self.assertTrue(coverage.available)
        self.assertEqual(coverage.covered_chains, 1)
        self.assertEqual(coverage.total_chains, 1)

    def test_gold_fields_are_rejected_at_search_boundary(self):
        with self.assertRaises(ValueError):
            SMOKE["validate_search_record"]({"question": "x", "answer": "y"})

    def test_mixed_chain_universe_counts_only_structurally_valid_records(self):
        _, chains = SMOKE["make_fixture"]()
        mixed = chains + [{"chain_id": "invalid", "uids": ["u1"]}]
        coverage = SMOKE["compute_chain_coverage"](["u1", "u2"], mixed)
        self.assertTrue(coverage.available)
        self.assertEqual(coverage.covered_chains, 1)
        self.assertEqual(coverage.total_chains, 1)

    def test_all_invalid_chain_universe_uses_original_ordering(self):
        from src.cpcr.proxy import compute_chain_coverage
        from src.cpcr.state_selection import retain_states, select_final_state

        coverage = compute_chain_coverage(["u1"], [{"uids": ["u1"]}])
        self.assertFalse(coverage.available)
        states = [
            {
                "selected_uids": ("coverage-first",),
                "completeness_proxy": 2,
                "proxy_available": False,
                "objective_score": 0.6,
                "path_atomic_edit_units": 1,
                "token_count": 2,
            },
            {
                "selected_uids": ("objective-first",),
                "completeness_proxy": 0,
                "proxy_available": False,
                "objective_score": 0.8,
                "path_atomic_edit_units": 1,
                "token_count": 2,
            },
        ]
        self.assertEqual(retain_states(states, width=2, enabled=True)[0]["selected_uids"], ("objective-first",))
        self.assertEqual(select_final_state(states, enabled=True)["selected_uids"], ("objective-first",))

    def test_cpcr_ordering_prioritizes_structural_coverage(self):
        from src.cpcr.state_selection import retain_states, select_final_state

        states = [
            {
                "selected_uids": ("objective-first",),
                "completeness_proxy": 0,
                "proxy_available": True,
                "objective_score": 0.9,
                "path_atomic_edit_units": 1,
                "token_count": 2,
            },
            {
                "selected_uids": ("coverage-first",),
                "completeness_proxy": 1,
                "proxy_available": True,
                "objective_score": 0.4,
                "path_atomic_edit_units": 1,
                "token_count": 2,
            },
        ]
        retained = retain_states(states, width=2, enabled=True)
        self.assertEqual(retained[0]["selected_uids"], ("coverage-first",))
        self.assertEqual(select_final_state(states, enabled=True)["selected_uids"], ("coverage-first",))

    def test_clean_a11_uses_its_own_beam_and_exact_final_keys(self):
        from src.cpcr.clean_factorial import choose_final, retain_beam

        states = [
            {
                "selected_uids": ("objective-first",),
                "completeness_proxy": 0,
                "proxy_available": True,
                "objective_score": 0.8,
                "path_atomic_edit_units": 1,
                "token_count": 2,
            },
            {
                "selected_uids": ("coverage-first",),
                "completeness_proxy": 1,
                "proxy_available": True,
                "objective_score": 0.4,
                "path_atomic_edit_units": 1,
                "token_count": 2,
            },
        ]
        self.assertEqual(retain_beam(states, width=2, coverage_priority=True)[0]["selected_uids"], ("coverage-first",))
        self.assertEqual(choose_final(states, coverage_priority=True)["selected_uids"], ("coverage-first",))

    def test_clean_final_key_uses_exact_objective_after_rounding_tie(self):
        from src.cpcr.clean_factorial import choose_final

        states = [
            {
                "selected_uids": ("lower-exact-score",),
                "completeness_proxy": 1,
                "proxy_available": True,
                "objective_score": 0.5,
                "path_atomic_edit_units": 1,
                "token_count": 2,
            },
            {
                "selected_uids": ("higher-exact-score",),
                "completeness_proxy": 1,
                "proxy_available": True,
                "objective_score": 0.5000000000004,
                "path_atomic_edit_units": 1,
                "token_count": 2,
            },
        ]
        self.assertEqual(choose_final(states, coverage_priority=True)["selected_uids"], ("higher-exact-score",))

    def test_r14_fixed_pool_runner_returns_four_cells_on_synthetic_data(self):
        from src.cpcr.factorial_search import run_one
        from src.cabes.base.fair_budgeted_search import WordTokenizer

        evidence, chains = SMOKE["make_fixture"]()
        record = {
            "question_id": "synthetic-1",
            "question": "Which entity connects Alpha and Beta?",
            "evidence": evidence,
            "chains": chains,
            "relevance": {"u1": 1.0, "u2": 0.9},
            "demand": {},
            "candidate_universe_sha256": "synthetic-fixture",
        }
        config = {"max_depth": 2, "max_path_atomic_edit_units": 4}
        cells = []
        for enabled in (False, True):
            rows, _ = run_one(record, config, WordTokenizer(), enabled)
            cells.extend(rows)
        self.assertEqual([row["cell"] for row in cells], ["A00", "A01", "A10", "A11"])
        self.assertTrue(all(row["actual_context_tokens"] <= 256 for row in cells))

    def test_smoke_run_selects_covered_state(self):
        SMOKE["main"]()
        output = (REPO / "results" / "smoke" / "level2_smoke.json").read_text(encoding="utf-8")
        self.assertIn('"status": "PASS"', output)
        self.assertIn('"proxy_available": true', output)
