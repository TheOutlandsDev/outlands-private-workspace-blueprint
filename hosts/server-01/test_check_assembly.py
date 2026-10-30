"""Reject real destinations, module drift, and unearned acceptance claims."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from check_assembly import check, MODULES


SOURCE = Path(__file__).resolve().parents[2]


class AssemblyFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        target = self.root / "hosts/server-01/assembly.example.json"
        target.parent.mkdir(parents=True)
        shutil.copyfile(SOURCE / "hosts/server-01/assembly.example.json", target)
        for path, _ in MODULES.values():
            guide = self.root / path
            guide.parent.mkdir(parents=True, exist_ok=True)
            guide.write_text("Fictional module guide\n", encoding="utf-8")
        self.fixture = target

    def mutate(self, action):
        data = json.loads(self.fixture.read_text(encoding="utf-8"))
        action(data)
        self.fixture.write_text(json.dumps(data), encoding="utf-8")

    def test_published_worksheet_passes(self):
        self.assertEqual(check(self.root), [])

    def test_real_route_and_metrics_target_rejected(self):
        self.mutate(lambda data: data["optional_route"].update(example_backend="https://private.test/"))
        self.assertIn("fictional_route_boundary", check(self.root))
        self.mutate(lambda data: data.update(real_targets_included=True))
        self.assertIn("independent_private_boundary", check(self.root))

    def test_unearned_acceptance_rejected(self):
        self.mutate(lambda data: data["modules"][1].update(status="PASS"))
        self.assertIn("unearned_result", check(self.root))

    def test_extra_module_or_field_rejected(self):
        self.mutate(lambda data: data["modules"].append({"id": "private-system", "path": "secret", "required": False, "status": "NOT_RUN"}))
        self.assertIn("module_set", check(self.root))
        self.mutate(lambda data: data.update(backup_provider="fictional"))
        self.assertIn("fictional_scope", check(self.root))


if __name__ == "__main__":
    unittest.main()
