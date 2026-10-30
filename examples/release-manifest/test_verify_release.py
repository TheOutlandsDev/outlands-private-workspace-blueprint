"""Offline contract tests for the fictional exact-file export."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import verify_release


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures"
PAYLOAD = (FIXTURE / "export" / "example.txt").read_bytes()


class ReleaseManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.export = self.base / "export"
        self.export.mkdir()
        (self.export / "example.txt").write_bytes(PAYLOAD)
        self.manifest = self.base / "manifest.json"
        self.document = {
            "schema_version": 1,
            "files": [{"path": "example.txt", "bytes": len(PAYLOAD),
                       "sha256": hashlib.sha256(PAYLOAD).hexdigest()}],
        }
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.document), encoding="utf-8")

    def assert_code(self, code):
        with self.assertRaises(verify_release.ReleaseError) as error:
            verify_release.verify(self.manifest, self.export)
        self.assertEqual(str(error.exception), code)

    def test_checked_in_fictional_fixture_passes_without_clearance(self):
        result = verify_release.verify(FIXTURE / "manifest.example.json",
                                       FIXTURE / "export")
        self.assertEqual(result["files_checked"], 1)
        self.assertEqual(result["bytes_checked"], 46)
        self.assertFalse(result["privacy_cleared"])
        self.assertFalse(result["rights_cleared"])

    def test_same_size_content_change_fails_hash(self):
        (self.export / "example.txt").write_bytes(b"X" + PAYLOAD[1:])
        self.assert_code("HASH_MISMATCH")

    def test_extra_and_missing_files_fail(self):
        (self.export / "surprise.txt").write_text("fictional", encoding="utf-8")
        self.assert_code("EXTRA_FILE")
        (self.export / "surprise.txt").unlink()
        (self.export / "example.txt").unlink()
        self.assert_code("MISSING_FILE")

    def test_links_fail(self):
        (self.export / "example.txt").unlink()
        (self.export / "example.txt").symlink_to(FIXTURE / "export" / "example.txt")
        self.assert_code("SYMLINK")
        (self.export / "example.txt").unlink()
        source = self.base / "source.txt"
        source.write_bytes(PAYLOAD)
        os.link(source, self.export / "example.txt")
        self.assert_code("HARDLINK")

    def test_unsafe_path_and_duplicate_json_key_fail(self):
        self.document["files"][0]["path"] = "../example.txt"
        self.write_manifest()
        self.assert_code("PATH")
        self.manifest.write_text('{"schema_version":1,"schema_version":1,"files":[]}',
                                 encoding="utf-8")
        self.assert_code("DUPLICATE_JSON_KEY")

    def test_cli_failure_omits_payload_and_path(self):
        (self.export / "example.txt").write_bytes(b"X" + PAYLOAD[1:])
        run = subprocess.run(
            [sys.executable, "-I", "-B", str(HERE / "verify_release.py"),
             str(self.manifest), str(self.export)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "ERROR: HASH_MISMATCH\n")
        self.assertEqual(run.stderr, "")


if __name__ == "__main__":
    unittest.main()
