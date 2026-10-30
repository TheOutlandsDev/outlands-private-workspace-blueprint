"""Ensure a copied real route or an unearned PASS cannot enter the fixture."""
from pathlib import Path
import tempfile
import unittest

from check_example import check


SOURCE = Path(__file__).resolve().parent


class AccessFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("module.json", "access-review.example.json"):
            (self.root / name).write_bytes((SOURCE / name).read_bytes())

    def change(self, name, old, new):
        path = self.root / name
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def test_published_fixture_passes(self):
        self.assertEqual(check(self.root), [])

    def test_real_route_shape_rejected(self):
        self.change("access-review.example.json", "https://workspace.example.invalid/", "https://workspace.private.test/")
        self.assertIn("fictional_route_boundary", check(self.root))

    def test_unearned_pass_rejected(self):
        self.change("access-review.example.json", '"status": "NOT_RUN"', '"status": "PASS"')
        self.assertIn("unearned_result", check(self.root))

    def test_missing_denial_rejected(self):
        self.change("access-review.example.json", '"id": "network_unassigned"', '"id": "owner_allowed"')
        self.assertIn("check_set", check(self.root))


if __name__ == "__main__":
    unittest.main()
