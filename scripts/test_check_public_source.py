"""Offline boundary checks for the public source screen."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_public_source


class PublicSourceBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        compose = self.root / "examples" / "homepage" / "compose.yaml"
        compose.parent.mkdir(parents=True)
        compose.write_text(
            'services:\n  homepage:\n    image: ${HOMEPAGE_IMAGE:?required}\n'
            '    ports:\n      - "127.0.0.1:3000:3000"\n',
            encoding="utf-8",
        )

    def run_screen(self):
        output = io.StringIO()
        with patch.object(check_public_source, "ROOT", self.root):
            with redirect_stdout(output):
                code = check_public_source.main()
        return code, json.loads(output.getvalue())

    def test_file_count_boundary_fails_closed(self):
        for index in range(191):
            (self.root / f"fixture-{index:03d}.txt").write_text("fictional\n",
                                                              encoding="utf-8")
        code, report = self.run_screen()
        self.assertEqual(code, 0)
        self.assertEqual(report["files_checked"], 192)
        self.assertEqual(report["findings"], [])

        (self.root / "one-more.txt").write_text("fictional\n", encoding="utf-8")
        code, report = self.run_screen()
        self.assertEqual(code, 1)
        self.assertEqual(report["files_checked"], 193)
        self.assertEqual(report["findings"], [{"check": "bounded_source_limit"}])
        self.assertNotIn("one-more.txt", json.dumps(report))

    def test_private_path_screen_remains_active(self):
        (self.root / "sample.txt").write_text("/" + "home/" + "fictional-user",
                                              encoding="utf-8")
        code, report = self.run_screen()
        self.assertEqual(code, 1)
        self.assertIn("private_home_or_service_path",
                      [finding["check"] for finding in report["findings"]])

    def test_secret_directory_is_rejected(self):
        secret = self.root / ".secrets" / "grafana-admin-password"
        secret.parent.mkdir()
        secret.write_text("fictional-test-value\n", encoding="utf-8")
        code, report = self.run_screen()
        self.assertEqual(code, 1)
        self.assertIn("private_file_type",
                      [finding["check"] for finding in report["findings"]])


if __name__ == "__main__":
    unittest.main()
