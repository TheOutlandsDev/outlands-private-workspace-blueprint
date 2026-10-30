"""Disposable boundary tests for the local pre-upload review aid."""

from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

import preupload_check as gate


class PreuploadCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / "stage"
        self.stage.mkdir()
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)
        self.manifest = self.root / "manifest.json"
        self.base_paths = self.root / "base-paths.json"
        self.private_terms = self.root / "private-terms.json"
        self.base_commit = "a" * 40
        self.files = {
            "README.md": b"# Fictional guide\n[Guide](docs/guide.md)\n",
            "docs/guide.md": b"This example uses invented values.\n",
        }
        self.write_stage()
        self.write_inputs()

    def write_stage(self):
        for name, data in self.files.items():
            path = self.stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def write_inputs(self):
        rows = [
            {"path": name, "sha256": hashlib.sha256(data).hexdigest(),
             "synthetic_fixture": name.endswith("guide.md")}
            for name, data in sorted(self.files.items())
        ]
        self.manifest.write_text(json.dumps({"schema_version": 1,
            "repository": "ExampleOrg/example-blueprint",
            "base_commit": self.base_commit, "files": rows}), encoding="utf-8")
        self.base_paths.write_text(json.dumps({"schema_version": 1,
            "base_commit": self.base_commit, "paths": ["LICENSE"]}), encoding="utf-8")
        self.private_terms.write_text(json.dumps({"schema_version": 1,
            "terms": ["fictional-vault"]}), encoding="utf-8")
        self.private_terms.chmod(0o600)

    def run_gate(self, name="receipt"):
        out = io.StringIO()
        destination = self.private / name
        with redirect_stdout(out):
            code = gate.main(["preupload_check.py", str(self.manifest), str(self.stage),
                              str(self.base_paths), str(self.private_terms), str(destination)])
        return code, out.getvalue(), destination

    def test_clean_text_export_produces_private_receipt_without_publication_approval(self):
        code, output, receipt = self.run_gate()
        self.assertEqual(code, 0)
        self.assertEqual(output, "PASS: files=2 findings=0 publication_authorized=false\n")
        report = json.loads((receipt / "report.json").read_text())
        self.assertEqual(report["findings"], [])
        self.assertFalse(report["publication_authorized"])
        self.assertEqual(report["manual_reviews"]["privacy"], "PENDING")
        self.assertEqual(os.stat(receipt).st_mode & 0o777, 0o700)
        for name in ("report.json", "REVIEW.md", "REVIEW.txt"):
            self.assertEqual(os.stat(receipt / name).st_mode & 0o777, 0o600)
        self.assertEqual((receipt / "REVIEW.md").read_bytes(),
                         (receipt / "REVIEW.txt").read_bytes())

    def test_changed_bytes_and_private_value_are_review_only_without_value_in_stdout(self):
        (self.stage / "docs/guide.md").write_text("private owner string: fictional-vault\n")
        code, output, receipt = self.run_gate()
        self.assertEqual(code, 1)
        self.assertNotIn("fictional-vault", output)
        checks = {item["check"] for item in json.loads((receipt / "report.json").read_text())["findings"]}
        self.assertEqual(checks, {"HASH_CHANGED", "PRIVATE_TERM"})

    def test_extra_file_and_missing_link_target_are_review_only(self):
        (self.stage / "README.md").write_text("[missing](docs/missing.md)\n")
        (self.stage / "extra.txt").write_text("invented\n")
        code, _output, receipt = self.run_gate()
        self.assertEqual(code, 1)
        checks = {item["check"] for item in json.loads((receipt / "report.json").read_text())["findings"]}
        self.assertEqual(checks, {"EXTRA_FILE", "HASH_CHANGED", "MISSING_LINK_TARGET"})

    def test_linked_stage_file_fails_closed_without_receipt(self):
        (self.stage / "docs/guide.md").unlink()
        (self.stage / "docs/guide.md").symlink_to(self.root / "outside.txt")
        code, output, receipt = self.run_gate()
        self.assertEqual(code, 2)
        self.assertEqual(output, "ERROR: LINK_OR_SPECIAL_FILE\n")
        self.assertFalse(receipt.exists())

    def test_base_commit_mismatch_is_reported(self):
        self.base_paths.write_text(json.dumps({"schema_version": 1,
            "base_commit": "b" * 40, "paths": []}), encoding="utf-8")
        code, _output, receipt = self.run_gate()
        self.assertEqual(code, 1)
        self.assertIn("BASE_COMMIT_MISMATCH", [item["check"] for item in
                      json.loads((receipt / "report.json").read_text())["findings"]])

    def test_private_path_and_email_are_coded_without_matched_values(self):
        private_text = "/" + "home/private-user\n" + "somebody@" + "private.invalid\n"
        (self.stage / "docs/guide.md").write_text(private_text)
        code, output, receipt = self.run_gate()
        self.assertEqual(code, 1)
        self.assertNotIn("private-user", output)
        report_text = (receipt / "report.json").read_text()
        self.assertNotIn("private-user", report_text)
        self.assertNotIn("somebody@", report_text)
        checks = {item["check"] for item in json.loads(report_text)["findings"]}
        self.assertEqual(checks, {"HASH_CHANGED", "PRIVATE_PATH", "NONEXAMPLE_EMAIL"})

    def test_binary_bytes_are_held_for_separate_review(self):
        (self.stage / "docs/guide.md").write_bytes(b"\xff\xd8fictional image bytes")
        code, _output, receipt = self.run_gate()
        self.assertEqual(code, 1)
        checks = {item["check"] for item in json.loads((receipt / "report.json").read_text())["findings"]}
        self.assertEqual(checks, {"HASH_CHANGED", "BINARY_REQUIRES_SEPARATE_REVIEW"})

    def test_reserved_example_address_passes_but_private_address_is_held(self):
        self.files["docs/guide.md"] = b"Fictional endpoint: 192.0.2.7\n"
        self.write_stage()
        self.write_inputs()
        self.assertEqual(self.run_gate("example-address")[0], 0)
        self.files["docs/guide.md"] = b"Fictional endpoint: 10." + b"1.2.3\n"
        self.write_stage()
        self.write_inputs()
        code, _output, receipt = self.run_gate("private-address")
        self.assertEqual(code, 1)
        self.assertIn("PRIVATE_NETWORK_ADDRESS", [item["check"] for item in
                      json.loads((receipt / "report.json").read_text())["findings"]])

    def test_existing_receipt_is_never_overwritten(self):
        self.assertEqual(self.run_gate()[0], 0)
        code, output, _receipt = self.run_gate()
        self.assertEqual(code, 2)
        self.assertEqual(output, "ERROR: INPUT_OR_OUTPUT\n")

    def test_receipt_parent_must_be_private(self):
        self.private.chmod(0o755)
        code, output, receipt = self.run_gate()
        self.assertEqual(code, 2)
        self.assertEqual(output, "ERROR: RECEIPT_PARENT_NOT_PRIVATE\n")
        self.assertFalse(receipt.exists())

    def test_private_terms_file_must_be_owner_only(self):
        self.private_terms.chmod(0o644)
        code, output, receipt = self.run_gate()
        self.assertEqual(code, 2)
        self.assertEqual(output, "ERROR: PRIVATE_TERMS_PERMISSIONS\n")
        self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
