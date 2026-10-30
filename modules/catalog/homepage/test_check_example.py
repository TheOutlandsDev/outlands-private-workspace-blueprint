"""Reject real links, host exposure, integrations, and filled public inputs."""
from pathlib import Path
import tempfile
import unittest

from check_example import check


SOURCE = Path(__file__).resolve().parent
FILES = (
    "compose.yaml", ".env.example", "module.json", "config/services.yaml",
    "config/settings.yaml", "config/widgets.yaml", "config/bookmarks.yaml",
    "assets/mark.svg", "assets/netwall.svg",
)


class CatalogBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((SOURCE / name).read_bytes())

    def change(self, name, old, new):
        path = self.root / name
        content = path.read_text(encoding="utf-8")
        self.assertIn(old, content)
        path.write_text(content.replace(old, new), encoding="utf-8")

    def test_published_catalog_passes(self):
        self.assertEqual(check(self.root), [])

    def test_wildcard_port_and_docker_socket_rejected(self):
        self.change("compose.yaml", "127.0.0.1:${CATALOG_PORT:?Set a free local port}:3000", "0.0.0.0:3003:3000")
        self.assertIn("catalog_loopback", check(self.root))
        self.change("compose.yaml", "./config:/app/config", "/var/run/docker.sock:/var/run/docker.sock")
        self.assertIn("host_or_network_access", check(self.root))

    def test_real_link_and_service_widget_rejected(self):
        self.change("config/services.yaml", "https://webui.example.invalid/", "https://real.private.test/")
        self.assertIn("fictional_links_only", check(self.root))
        self.change("config/services.yaml", "    - Grafana:", "    - Grafana:\n        widget: grafana")
        self.assertIn("links_not_integrations", check(self.root))

    def test_filled_public_image_or_identity_rejected(self):
        self.change(".env.example", "HOMEPAGE_IMAGE=\n", "HOMEPAGE_IMAGE=unreviewed:latest\n")
        self.assertIn("nonblank_public_HOMEPAGE_IMAGE", check(self.root))
        self.change(".env.example", "PUID=\n", "PUID=1000\n")
        self.assertIn("nonblank_public_PUID", check(self.root))

    def test_artwork_change_rejected(self):
        self.change("assets/mark.svg", "OUTLANDS original mark", "altered mark")
        self.assertIn("reviewed_artwork_changed", check(self.root))


if __name__ == "__main__":
    unittest.main()
