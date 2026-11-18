"""Offline reference-only checks; no TradingAgents imports, model or HTTP calls."""

import ast
import copy
import json
import unittest
from pathlib import Path

import build_reference as reference
import validate_reference as validation

ROOT = Path(__file__).resolve().parent


class ReferenceTests(unittest.TestCase):
    def test_raw_sources_and_manifest_are_consistent(self):
        result = validation.verify()
        self.assertTrue(result["consistency_pass"])
        self.assertFalse(result["stage_a_pass"])
        self.assertFalse(result["frozen"])

    def test_expected_display_literals_independently_reviewable(self):
        rows = {row["reference_id"]: row for row in validation.load("expected_metrics.json")}
        expected = {
            "aapl.revenue_yoy_q": "9.6", "aapl.revenue_yoy_a": "2.0", "aapl.revenue_qoq": "-1.4",
            "aapl.gross_margin": "46.5", "aapl.operating_margin": "30.0", "aapl.net_margin": "24.9",
            "aapl.current_ratio": "0.9", "aapl.liabilities_to_assets": "80.1", "aapl.fcf_reported_span": "72281", "aapl.pe_fy": "33.4",
            "xom.revenue_yoy_q": "-12.4", "xom.revenue_yoy_a": "1.5", "xom.revenue_qoq": "-2.0",
            "xom.gross_margin": "n/a", "xom.operating_margin": "n/a", "xom.net_margin": "8.7",
            "xom.current_ratio": "1.2", "xom.liabilities_to_assets": "39.7", "xom.fcf_reported_span": "12322", "xom.pe_fy": "13.7",
        }
        self.assertEqual({key: row["expected_display"] for key, row in rows.items()}, expected)

    def test_prior_fact_fiscal_position_not_copied_from_filing(self):
        fact = validation.load("selected_facts.json")["aapl.rev.q3.2024"]
        self.assertEqual(fact["carrying_filing_fy"], 2025)
        self.assertEqual(fact["fiscal_year"], 2024)
        self.assertEqual(fact["fiscal_quarter"], 3)

    def test_eps_sign_and_reported_span_evidence(self):
        facts = validation.load("selected_facts.json")
        for issuer in ("aapl", "xom"):
            self.assertEqual(facts[f"{issuer}.eps.fy2024"]["unit"], "USD/shares")
            self.assertEqual(facts[f"{issuer}.eps.fy2024"]["raw_scale"], "0")
            self.assertEqual(facts[f"{issuer}.capex.ytd"]["raw_ix_sign"], "+")
            self.assertIn("(", facts[f"{issuer}.capex.ytd"]["statement_row"])
            self.assertEqual(facts[f"{issuer}.capex.ytd"]["span"], "ytd")
        self.assertEqual(facts["aapl.rev.fy2024"]["duration_days_inclusive"], 364)
        self.assertEqual(facts["aapl.rev.fy2023"]["duration_days_inclusive"], 371)

    def test_real_record_control_witnesses_are_not_application_results(self):
        self.assertEqual(len(validation.witness_checks()), 12)
        for path in (ROOT / "controlled_variants").glob("*.json"):
            case = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(case["is_real_disclosure"])
            self.assertFalse(case["application_test_executed"])

    def test_price_date_basis_and_no_dividend_adjusted_close(self):
        prices = validation.load("price_records.json")
        for price in prices.values():
            self.assertEqual(price["actual_price_date"], "2025-08-04")
            self.assertEqual(price["currency"], "USD")
            self.assertNotEqual(price["value"], price["adjclose_not_used"])
            self.assertEqual(price["share_basis_evidence"]["split_events"], {})

    def test_tampered_manifest_is_rejected_without_rewrite(self):
        manifest = copy.deepcopy(validation.load("reference_manifest.json"))
        manifest["files"][next(iter(manifest["files"]))] = "0" * 64
        with self.assertRaisesRegex(ValueError, "manifest_projection_digest_mismatch"):
            validation.verify_manifest(manifest)

    def test_reference_scripts_do_not_import_application_or_make_implicit_http_calls(self):
        for name in ("build_reference.py", "inspect_saved_filings.py", "assemble_review.py", "validate_reference.py"):
            tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imports = [node.module or ""]
                else:
                    continue
                self.assertFalse(any(module.startswith(("tradingagents", "requests", "urllib", "openai")) for module in imports))

    def test_half_up_and_negative_financial_values(self):
        self.assertEqual(reference.arithmetic("-10.05", "1", "ratio")[0], "-10.1")
        self.assertEqual(reference.arithmetic("5000000", "10000000", "fcf")[0], "-5")


if __name__ == "__main__":
    unittest.main()
