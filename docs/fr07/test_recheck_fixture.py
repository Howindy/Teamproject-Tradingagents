"""Tests of the independent preparation script; not FR-07 application tests."""

import unittest

from recheck_fixture import audit, independent_arithmetic


class ArithmeticPreparationTests(unittest.TestCase):
    def test_recorded_fixture_displays_recompute_independently(self):
        result = audit()
        self.assertTrue(result["arithmetic_pass"])
        self.assertEqual(len(result["rows"]), 12)

    def test_required_growth_example(self):
        self.assertEqual(independent_arithmetic("96221", "46743", "growth")[0], "105.9")

    def test_negative_profit_and_fcf_are_not_arithmetic_errors(self):
        self.assertEqual(independent_arithmetic("-10", "100", "percentage")[0], "-10.0")
        self.assertEqual(independent_arithmetic("5", "10", "difference")[0], "-5")

    def test_positive_and_negative_half_up(self):
        self.assertEqual(independent_arithmetic("10.05", "1", "ratio")[0], "10.1")
        self.assertEqual(independent_arithmetic("-10.05", "1", "ratio")[0], "-10.1")

    def test_arithmetic_does_not_claim_gate_pass_or_application_implementation(self):
        result = audit()
        self.assertEqual(result["stage_a"], "BLOCKED")
        self.assertEqual(result["human_review"], "pending")
        self.assertFalse(result["application_implementation_started"])
        self.assertTrue(result["stage_a_blockers"])
        self.assertTrue(result["fixture_issues"])


if __name__ == "__main__":
    unittest.main()
