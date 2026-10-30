"""Negative boundary checks for the synthetic AI module."""
from pathlib import Path
import tempfile
import unittest

from check_example import check


SOURCE = Path(__file__).resolve().parent


class ExampleBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("compose.yaml", "compose.nvidia.yaml", ".env.example", "module.json", "inference.example.json"):
            (self.root / name).write_bytes((SOURCE / name).read_bytes())

    def change(self, name, old, new):
        path = self.root / name
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new))

    def test_published_example_passes(self):
        self.assertEqual(check(self.root), [])

    def test_ollama_host_port_is_rejected(self):
        self.change("compose.yaml", "  ollama:\n", "  ollama:\n    ports:\n      - '11434:11434'\n")
        self.assertIn("ollama_host_exposure", check(self.root))

    def test_webui_wildcard_bind_is_rejected(self):
        self.change("compose.yaml", "127.0.0.1:${WEBUI_PORT:?Set WEBUI_PORT}:8080", "0.0.0.0:3001:8080")
        self.assertIn("webui_loopback", check(self.root))

    def test_filled_public_secret_is_rejected(self):
        self.change(".env.example", "WEBUI_SECRET_KEY=\n", "WEBUI_SECRET_KEY=example-value\n")
        self.assertIn("nonblank_public_WEBUI_SECRET_KEY", check(self.root))

    def test_gpu_override_cannot_expose_ollama_or_request_all_devices(self):
        self.change("compose.nvidia.yaml", "count: 1", "count: all")
        self.assertIn("gpu_profile_boundary", check(self.root))
        self.change("compose.nvidia.yaml", "  ollama:\n", "  ollama:\n    ports: ['11434:11434']\n")
        self.assertIn("gpu_profile_boundary", check(self.root))

    def test_real_model_reference_and_unearned_result_rejected(self):
        self.change("inference.example.json", '"model_reference": ""', '"model_reference": "private-model"')
        self.assertIn("fictional_inference_boundary", check(self.root))
        self.change("inference.example.json", '"status": "NOT_RUN"', '"status": "PASS"')
        self.assertIn("unearned_inference_result", check(self.root))


if __name__ == "__main__":
    unittest.main()
