"""Offline refusal tests for the disposable model pull and inference gate."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from check_inference import (EXPECTED_DIGEST, MODEL, PROJECT, check, invoke,
                             main, validate_generation, validate_model)


DIGEST = EXPECTED_DIGEST + "0" * (64 - len(EXPECTED_DIGEST))


class InferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        folder = self.root / "ai-restored"
        folder.mkdir()
        (folder / ".env").write_text("fictional fixture\n", encoding="utf-8")

    def fake(self, *, digest=DIGEST, devices="null", generated=None):
        metadata = {"count": 1, "name": MODEL, "digest": digest, "size": 271_000_000}
        responses = [json.dumps({"name": PROJECT}), "a" * 64, devices, "",
                     json.dumps(metadata), json.dumps(generated or {"done": True, "nonempty": True})]
        calls = []

        def runner(command, **kwargs):
            calls.append(command)
            return responses.pop(0)

        return runner, calls

    def test_success_requires_cpu_boundary_reviewed_digest_and_nonempty_result(self):
        runner, calls = self.fake()
        output = io.StringIO()
        with redirect_stdout(output):
            check(self.root, runner)
        self.assertEqual(len(calls), 6)
        self.assertIn("pull", calls[3])
        self.assertIn(MODEL, calls[3])
        self.assertIn("PASS disposable CPU inference", output.getvalue())
        self.assertNotIn("fictional red paper kite", output.getvalue())

    def test_digest_change_stops_before_generation(self):
        runner, calls = self.fake(digest="f" * 64)
        with redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "identity or size changed"):
                check(self.root, runner)
        self.assertEqual(len(calls), 5)

    def test_gpu_request_stops_before_model_pull(self):
        runner, calls = self.fake(devices='[{"Driver":"nvidia"}]')
        with self.assertRaisesRegex(RuntimeError, "CPU-only"):
            check(self.root, runner)
        self.assertEqual(len(calls), 3)

    def test_empty_or_incomplete_generation_is_rejected(self):
        for result in ({"done": True, "nonempty": False},
                       {"done": False, "nonempty": True}):
            with self.subTest(result=result):
                with self.assertRaisesRegex(RuntimeError, "response incomplete"):
                    validate_generation(result)

    def test_oversized_or_extra_model_is_rejected(self):
        for change in ({"size": 400_000_000}, {"count": 2}):
            with self.subTest(change=change):
                data = {"count": 1, "name": MODEL, "digest": DIGEST,
                        "size": 271_000_000, **change}
                with self.assertRaisesRegex(RuntimeError, "identity or size changed"):
                    validate_model(data)

    def test_subprocess_failure_does_not_print_captured_output(self):
        class Failed:
            returncode = 1
            stdout = "private output"

        with patch("check_inference.subprocess.run", return_value=Failed()):
            with self.assertRaisesRegex(RuntimeError, "disposable inference operation failed") as caught:
                invoke(["docker", "version"])
        self.assertNotIn("private output", str(caught.exception))

    def test_entrypoint_refuses_local_invocation(self):
        with patch.dict(os.environ, {}, clear=True), redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 2)


if __name__ == "__main__":
    unittest.main()
