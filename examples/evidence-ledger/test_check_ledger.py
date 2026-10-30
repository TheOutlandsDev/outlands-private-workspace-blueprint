"""Contract checks for the offline ledger example."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("check_ledger.py")
EXAMPLE = Path(__file__).with_name("ledger.example.json")


def run_document(document):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "ledger.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-I", "-B", str(SCRIPT), str(path)],
            capture_output=True, text=True, check=False,
        )


class LedgerContractTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_fictional_example_does_not_claim_a_pass(self):
        result = run_document(self.document)
        self.assertEqual(result.returncode, 0)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["statuses"]["PASS"], 0)
        self.assertEqual(summary["statuses"]["NOT_RUN"], 5)
        self.assertFalse(summary["evidence_verified"])

    def test_claimed_pass_requires_matching_evidence_stage(self):
        check = self.document["checks"][0]
        check["status"] = "PASS"
        check["evidence"] = {"kind": "browser-observation", "reference": "fictional record"}
        wrong = run_document(self.document)
        self.assertEqual(wrong.returncode, 2)
        self.assertIn("EVIDENCE_STAGE", wrong.stdout)
        check["evidence"]["kind"] = "source-check"
        valid = run_document(self.document)
        self.assertEqual(valid.returncode, 0)
        self.assertEqual(json.loads(valid.stdout)["statuses"]["PASS"], 1)

    def test_duplicate_check_and_unrun_evidence_are_rejected(self):
        self.document["checks"][1]["id"] = self.document["checks"][0]["id"]
        self.assertIn("DUPLICATE_CHECK_ID", run_document(self.document).stdout)
        self.document["checks"][1]["id"] = "owner-login"
        self.document["checks"][1]["evidence"] = {
            "kind": "access-observation", "reference": "fictional record"}
        self.assertIn("UNRUN_EVIDENCE", run_document(self.document).stdout)

    def test_duplicate_json_key_is_rejected_without_echo(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            path.write_text('{"schema_version":1,"schema_version":2}', encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(SCRIPT), str(path)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), "ERROR: DUPLICATE_JSON_KEY")


if __name__ == "__main__":
    unittest.main()
