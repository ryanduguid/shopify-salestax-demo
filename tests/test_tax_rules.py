from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Importing oa_client only reads environment variables; it makes no requests.
from oa_client import _MOCK_SKILL


def bundled_skill():
    return next(iter(_MOCK_SKILL.values()))

import nexus_check


class IllinoisThresholdTests(unittest.TestCase):
    def result(self, sales, orders, home=False, registered=False):
        return nexus_check.check({"state": "IL", "sales": sales, "orders": orders,
            "tax_collected": 0, "home_state": home, "registered": registered}, bundled_skill())

    def test_transaction_limb_removed(self):
        for orders in (199, 200, 201, 10000):
            with self.subTest(orders=orders):
                self.assertIn("no economic nexus", self.result(50000, orders)["headline"])

    def test_receipts_boundary_is_inclusive(self):
        self.assertNotIn("CROSSED", self.result(99999.99, 201)["headline"])
        self.assertIn("CROSSED", self.result(100000, 1)["headline"])

    def test_physical_nexus_preserved(self):
        self.assertEqual(self.result(1, 1, home=True)["status"], "warn")
        self.assertEqual(self.result(1, 1, home=True, registered=True)["status"], "ok")

    def test_dated_fixture(self):
        self.assertEqual(bundled_skill()["rules"]["thresholds"]["IL"]["effective_from"], "2026-01-01")
