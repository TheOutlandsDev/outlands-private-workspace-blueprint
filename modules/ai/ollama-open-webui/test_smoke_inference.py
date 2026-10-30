"""Offline contract tests; Docker is replaced by a fictional command runner."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from smoke_inference import PROMPT, check


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".env").write_text("OLLAMA_IMAGE=fictional\n")
        (self.root / ".env").chmod(0o600)
        self.calls = []

    def runner(self, command, **kwargs):
        self.calls.append(command)
        if command[-1] == "ls":
            return subprocess.CompletedProcess(command, 0,
                                               "NAME ID SIZE\nfixture-model:latest abc 1GB\n", "")
        return subprocess.CompletedProcess(command, 0, "A fictional red paper kite flies.\n", "")

    def test_installed_model_gets_fictional_prompt_without_pull(self):
        result = check("fixture-model:latest", self.root, runner=self.runner)
        self.assertTrue(result.startswith("PASS:"))
        self.assertEqual([call[-2:] for call in self.calls[:2]],
                         [["config", "--quiet"], ["ollama", "ls"]])
        self.assertEqual(self.calls[2][-3:],
                         ["run", "fixture-model:latest", PROMPT])
        self.assertFalse(any("pull" in call for call in self.calls))

    def test_missing_model_stops_before_run(self):
        with self.assertRaisesRegex(ValueError, "absent"):
            check("different-model", self.root, runner=self.runner)
        self.assertEqual(len(self.calls), 2)

    def test_empty_response_fails(self):
        def runner(command, **kwargs):
            value = self.runner(command, **kwargs)
            if "run" in command:
                value.stdout = "  "
            return value

        with self.assertRaisesRegex(ValueError, "empty"):
            check("fixture-model:latest", self.root, runner=runner)

    def test_private_input_and_env_are_required(self):
        for model in ("", "-unsafe", "model with spaces"):
            with self.subTest(model=model), self.assertRaises(ValueError):
                check(model, self.root, runner=self.runner)
        (self.root / ".env").chmod(0o644)
        with self.assertRaisesRegex(ValueError, "mode-0600"):
            check("fixture-model:latest", self.root, runner=self.runner)
        self.assertEqual(self.calls, [])

    def test_gpu_overlay_is_explicit(self):
        check("fixture-model:latest", self.root, gpu=True, runner=self.runner)
        self.assertIn("compose.nvidia.yaml", self.calls[0])


if __name__ == "__main__":
    unittest.main()
