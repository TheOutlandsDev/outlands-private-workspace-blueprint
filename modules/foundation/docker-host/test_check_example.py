"""Negative checks for the foundation fixture's host boundary."""
from pathlib import Path
import tempfile
import unittest

from check_example import check


SOURCE = Path(__file__).resolve().parent


class FoundationBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("compose.yaml", ".env.example", "module.json"):
            (self.root / name).write_bytes((SOURCE / name).read_bytes())

    def change(self, name, old, new):
        path = self.root / name
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def test_published_fixture_passes(self):
        self.assertEqual(check(self.root), [])

    def test_host_network_is_rejected(self):
        self.change("compose.yaml", "network_mode: none", "network_mode: host")
        self.assertIn("host_exposure", check(self.root))

    def test_published_port_is_rejected(self):
        self.change("compose.yaml", "    read_only: true", "    ports: ['8080:80']\n    read_only: true")
        self.assertIn("host_exposure", check(self.root))

    def test_filled_public_input_is_rejected(self):
        self.change(".env.example", "SMOKE_IMAGE=\n", "SMOKE_IMAGE=some-image\n")
        self.assertIn("nonblank_public_image", check(self.root))


if __name__ == "__main__":
    unittest.main()
