import ast
from pathlib import Path
import unittest


def bundled_skill():
    # Read only the literal fixture; do not initialise authenticated clients.
    tree = ast.parse(Path("oa_client.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_MOCK_SKILL" for t in node.targets):
            return next(iter(ast.literal_eval(node.value).values()))
    raise AssertionError("Missing bundled rule fixture")

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
