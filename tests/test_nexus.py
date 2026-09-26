import contextlib
import copy
import io
import os
import unittest
from unittest.mock import patch

os.environ["OA_MCP_TOKEN"] = ""
os.environ["OA_MCP_URL"] = "https://example.invalid"

import nexus_check
import pipeline
import shopify_client
from oa_client import OAClient


class NexusTests(unittest.TestCase):
    def setUp(self):
        self.network = patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.skill = copy.deepcopy(OAClient(token=None).get_skill("us-sales-tax-nexus"))

    def record(self, state="IL", **changes):
        periods = {"IL": ("2025-07-01", "2026-06-30", "il_tpp_gross_receipts"),
                   "NY": ("2025-09-01", "2026-08-31", "ny_tpp_gross_receipts"),
                   "CA": ("2026-01-01", "2026-09-26", "ca_related_tpp_sales"),
                   "PA": ("2025-01-01", "2025-12-31", "pa_eligible_gross_sales"),
                   "FL": ("2025-01-01", "2025-12-31", "fl_taxable_remote_sales"),
                   "TX": ("2025-09-01", "2026-08-31", "tx_total_revenue")}
        start, end, basis = periods.get(state, periods["IL"])
        return {"state": state, "period_sales": "100000", "period_orders": 101,
                "prior_year_sales": "0", "tax_collected": "0", "registered": False,
                "home_state": False, "assessment_date": "2026-09-26", "period_start": start,
                "period_end": end, "sales_basis": basis, **changes}

    def result(self, state="IL", **changes):
        return nexus_check.check(shopify_client.normalize(self.record(state, **changes)), self.skill)

    def test_amount_boundaries(self):
        for state, threshold, equality in (("IL", 100000, True), ("PA", 100000, True),
                                           ("FL", 100000, False), ("CA", 500000, False),
                                           ("NY", 500000, False)):
            for amount, met in ((threshold - 1, False), (threshold, equality), (threshold + 1, True)):
                with self.subTest(state=state, amount=amount):
                    self.assertIs(self.result(state, period_sales=str(amount))["threshold_met"], met)

    def test_new_york_requires_both_strict_comparisons(self):
        for amount, orders, met in (("500001", 100, False), ("500000", 101, False),
                                    ("500001", 101, True), ("520000", 90, False)):
            with self.subTest(amount=amount, orders=orders):
                self.assertIs(self.result("NY", period_sales=amount, period_orders=orders)["threshold_met"], met)

    def test_illinois_no_longer_uses_transaction_count(self):
        self.assertIs(self.result(period_sales="1", period_orders=1000)["threshold_met"], False)
        self.assertIs(self.result(period_sales="100000", period_orders=0)["threshold_met"], True)

    def test_california_checks_each_year_separately(self):
        self.assertIs(self.result("CA", period_sales="1", prior_year_sales="500001")["threshold_met"], True)
        self.assertIs(self.result("CA", period_sales="300000", prior_year_sales="300000")["threshold_met"], False)
        self.assertIsNone(self.result("CA", prior_year_sales=None)["threshold_met"])

    def test_texas_equality_requires_review(self):
        self.assertIs(self.result("TX", period_sales="499999.99")["threshold_met"], False)
        self.assertIsNone(self.result("TX", period_sales="500000")["threshold_met"])
        self.assertFalse(self.result("TX", period_sales="500000")["complete"])
        self.assertIs(self.result("TX", period_sales="500000.01")["threshold_met"], True)

    def test_missing_dates_basis_and_totals_remain_unknown(self):
        for changes in ({"assessment_date": None}, {"period_start": None}, {"period_end": None},
                        {"sales_basis": None}, {"period_sales": None}, {"sales_basis": "all_orders"},
                        {"assessment_date": "2027-01-01"}, {"assessment_date": "2025-12-31"},
                        {"period_start": "2025-01-01"}):
            with self.subTest(changes=changes):
                result = self.result(**changes)
                self.assertIsNone(result["threshold_met"])
                self.assertFalse(result["complete"])

    def test_periods_use_state_quarters_and_calendar_months(self):
        result = self.result("NY", assessment_date="2026-03-01", period_start="2025-03-01", period_end="2026-02-28")
        self.assertIs(result["threshold_met"], False)
        self.assertIsNone(self.result("NY", period_start="2025-07-01", period_end="2026-06-30")["threshold_met"])
        self.assertIsNone(self.result("TX", period_end="2026-09-26")["threshold_met"])

    def test_registration_and_home_state_never_prove_collection(self):
        for registered, home in ((True, False), (False, True), (True, True)):
            with self.subTest(registered=registered, home=home):
                result = self.result(registered=registered, home_state=home)
                self.assertIs(result["threshold_met"], True)
                self.assertNotIn("collecting ✓", result["headline"] + result["detail"])
                self.assertNotIn("no obligation", result["detail"])

    def test_missing_reporting_facts_do_not_discard_known_comparison(self):
        for changes in ({"registered": None}, {"home_state": None}, {"tax_collected": None}):
            with self.subTest(changes=changes):
                result = self.result(**changes)
                self.assertIs(result["threshold_met"], True)
                self.assertFalse(result["complete"])
        self.assertTrue(self.result(period_sales=0, tax_collected=0)["complete"])

    def test_invalid_values_and_dates_are_rejected(self):
        for field in ("registered", "home_state"):
            for value in ("false", 0, 1):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.result(**{field: value})
        for field, value in (("period_sales", True), ("period_sales", "NaN"), ("period_sales", -1),
                             ("period_sales", "0.001"), ("period_orders", 1.5),
                             ("assessment_date", "2026-02-30"), ("assessment_date", "20260926")):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.result(**{field: value})

    def test_unknown_state_and_rule_contract_are_incomplete(self):
        self.assertFalse(self.result("ZZ")["complete"])
        self.skill["rules"] = {}
        self.assertIsNone(self.result()["threshold_met"])

    def test_pipeline_keeps_other_rows_and_prints_reporting_facts(self):
        rows = [self.record(registered="false"), self.record(registered=True),
                self.record("NY", period_sales="520000", period_orders=90)]
        output = io.StringIO()
        with patch.object(shopify_client, "extract", return_value=rows), contextlib.redirect_stdout(output):
            self.assertFalse(pipeline.run("unused.json", OAClient(token=None)))
        text = output.getvalue()
        for expected in ("invalid input", "Registration reported: yes", "Tax collected reported: USD 0.00",
                         "NY", "unverified sample rules"):
            self.assertIn(expected, text)
        self.assertNotIn("signed off", text)

    def test_default_cli_selects_offline_mode_explicitly(self):
        with patch.object(pipeline, "OAClient", return_value=OAClient(token=None)) as constructor:
            with patch.object(pipeline, "run", return_value=True), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pipeline.main(["pipeline.py"]), 0)
        constructor.assert_called_once_with(token=None)

    def test_invalid_independent_fields_keep_the_known_state_comparison(self):
        for changes, expected in (({"tax_collected": -1}, "Tax collected reported: unknown"),
                                  ({"registered": "false"}, "Registration reported: unknown"),
                                  ({"period_orders": 1.5}, "Home state reported: no")):
            with self.subTest(changes=changes):
                row = self.record(**changes)
                output = io.StringIO()
                with patch.object(shopify_client, "extract", return_value=[row]), contextlib.redirect_stdout(output):
                    self.assertFalse(pipeline.run("unused.json", OAClient(token=None)))
                self.assertIn("invalid input", output.getvalue())
                self.assertIn("Supplied totals meet the modelled threshold", output.getvalue())
                self.assertIn(expected, output.getvalue())

    def test_invalid_new_york_count_prevents_only_its_required_comparison(self):
        output = io.StringIO()
        row = self.record("NY", period_sales="600000", period_orders=1.5, registered=True)
        with patch.object(shopify_client, "extract", return_value=[row]), contextlib.redirect_stdout(output):
            self.assertFalse(pipeline.run("unused.json", OAClient(token=None)))
        self.assertIn("Threshold comparison incomplete", output.getvalue())
        self.assertIn("Registration reported: yes", output.getvalue())
        self.assertIn("period_orders", output.getvalue())


if __name__ == "__main__":
    unittest.main()
