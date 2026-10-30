"""Privacy and state-separation checks for the fictional telemetry source."""
from pathlib import Path
import tempfile
import unittest

from check_example import check
from metrics_server import render


SOURCE = Path(__file__).resolve().parent
FILES = (
    "compose.yaml", ".env.example", "prometheus.yml", "module.json",
    "provisioning/datasources/prometheus.yml", "provisioning/dashboards/dashboards.yml",
    "dashboards/synthetic-source.json",
)


class SyntheticMetricsTests(unittest.TestCase):
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
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def test_published_fixture_passes(self):
        self.assertEqual(check(self.root), [])

    def test_wildcard_prometheus_port_is_rejected(self):
        self.change("compose.yaml", "127.0.0.1:${PROMETHEUS_PORT:?Set PROMETHEUS_PORT}:9090", "0.0.0.0:9090:9090")
        self.assertIn("loopback_ports", check(self.root))

    def test_external_scrape_target_is_rejected(self):
        self.change("prometheus.yml", 'targets: ["fixture:8000"]', 'targets: ["other-host:8000"]')
        self.assertIn("fictional_scrape_only", check(self.root))

    def test_dashboard_query_scope_is_rejected(self):
        self.change("dashboards/synthetic-source.json", "outlands_demo_value", "node_cpu_seconds_total")
        self.assertIn("dashboard_queries", check(self.root))

    def test_fresh_stale_and_unavailable_are_distinct(self):
        now = 2_000_000_000
        fresh_code, fresh = render("fresh", now)
        stale_code, stale = render("stale", now)
        unavailable_code, unavailable = render("unavailable", now)
        self.assertEqual((fresh_code, stale_code, unavailable_code), (200, 200, 503))
        self.assertIn(str(now).encode(), fresh)
        self.assertIn(str(now - 600).encode(), stale)
        self.assertNotIn(b"outlands_demo_value", unavailable)

    def test_unknown_mode_fails_closed(self):
        with self.assertRaises(ValueError):
            render("real", 2_000_000_000)


if __name__ == "__main__":
    unittest.main()
