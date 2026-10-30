"""Offline contract tests for the explicit-allowlist manifest creator."""

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

import create_manifest
import verify_release


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures"
PAYLOAD = (FIXTURE / "export" / "example.txt").read_bytes()


class CreateManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.export = self.base / "export"
        self.export.mkdir()
        (self.export / "example.txt").write_bytes(PAYLOAD)
        self.allowlist = self.base / "allowlist.json"
        self.document = {"schema_version": 1, "paths": ["example.txt"]}
        self.write_allowlist()
        self.output = self.base / "manifest.json"

    def write_allowlist(self):
        self.allowlist.write_text(json.dumps(self.document), encoding="utf-8")

    def assert_code(self, code):
        with self.assertRaises(create_manifest.CreateError) as error:
            create_manifest.create(self.allowlist, self.export, self.output)
        self.assertEqual(str(error.exception), code)

    def test_fictional_manifest_matches_fixture_and_verifies(self):
        result = create_manifest.create(FIXTURE / "allowlist.example.json",
                                        FIXTURE / "export", self.output)
        self.assertEqual(result["files_checked"], 1)
        self.assertEqual(result["bytes_checked"], 46)
        self.assertFalse(result["privacy_cleared"])
        self.assertFalse(result["rights_cleared"])
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")),
                         json.loads((FIXTURE / "manifest.example.json").read_text(
                             encoding="utf-8")))
        self.assertEqual(verify_release.verify(self.output, FIXTURE / "export")["result"],
                         "PASS")
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode) & 0o077, 0)

    def test_unlisted_and_missing_files_fail_before_output(self):
        (self.export / "extra.txt").write_text("fictional", encoding="utf-8")
        self.assert_code("EXTRA_FILE")
        self.assertFalse(self.output.exists())
        (self.export / "extra.txt").unlink()
        (self.export / "example.txt").unlink()
        self.assert_code("MISSING_FILE")
        self.assertFalse(self.output.exists())

    def test_links_fail_before_output(self):
        (self.export / "example.txt").unlink()
        (self.export / "example.txt").symlink_to(FIXTURE / "export" / "example.txt")
        self.assert_code("SYMLINK")
        (self.export / "example.txt").unlink()
        source = self.base / "source.txt"
        source.write_bytes(PAYLOAD)
        os.link(source, self.export / "example.txt")
        self.assert_code("HARDLINK")
        self.assertFalse(self.output.exists())

    def test_unsafe_and_duplicate_allowlist_paths_fail(self):
        self.document["paths"] = ["../example.txt"]
        self.write_allowlist()
        self.assert_code("PATH")
        self.document["paths"] = ["example.txt", "example.txt"]
        self.write_allowlist()
        self.assert_code("DUPLICATE_PATH")
        self.allowlist.write_text('{"schema_version":1,"schema_version":1,"paths":[]}',
                                  encoding="utf-8")
        self.assert_code("DUPLICATE_JSON_KEY")

    def test_output_is_outside_and_never_overwritten(self):
        self.output.write_text("existing", encoding="utf-8")
        self.assert_code("OUTPUT_EXISTS")
        self.assertEqual(self.output.read_text(encoding="utf-8"), "existing")
        self.output = self.export / "manifest.json"
        self.assert_code("LOCATION")
        self.assertFalse(self.output.exists())
        alias = self.base / "export-alias"
        alias.symlink_to(self.export, target_is_directory=True)
        self.output = alias / "manifest.json"
        self.assert_code("LOCATION")
        self.assertFalse(self.output.exists())
        self.output = self.base / "fresh.json"
        self.allowlist = self.export / "allowlist.json"
        self.write_allowlist()
        self.assert_code("LOCATION")
        self.assertFalse(self.output.exists())

    def test_oversized_file_and_directory_fanout_fail(self):
        (self.export / "example.txt").write_bytes(b"X" * (create_manifest.MAX_FILE_BYTES + 1))
        self.assert_code("FILE_SIZE")
        (self.export / "example.txt").write_bytes(PAYLOAD)
        for index in range(create_manifest.MAX_ENTRIES + 1):
            (self.export / f"empty-{index:03d}").mkdir()
        self.assert_code("ENTRY_COUNT")
        self.assertFalse(self.output.exists())

    def test_cli_failure_prints_only_fixed_code(self):
        (self.export / "extra.txt").write_text("fictional", encoding="utf-8")
        run = subprocess.run(
            [sys.executable, "-I", "-B", str(HERE / "create_manifest.py"),
             str(self.allowlist), str(self.export), str(self.output)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "ERROR: EXTRA_FILE\n")
        self.assertEqual(run.stderr, "")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
