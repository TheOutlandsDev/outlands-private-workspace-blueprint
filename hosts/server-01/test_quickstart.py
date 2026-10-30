"""Exercise local-context refusal and additive private-copy boundaries offline."""

from pathlib import Path
import shutil
from types import SimpleNamespace
import tempfile
import unittest

from preflight import check
from prepare_local import BLANK_INPUTS, FILES, ROOT, SOURCES, prepare
from check_assembly import MODULES


class PreflightTests(unittest.TestCase):
    def test_local_context_and_read_only_probes(self):
        calls = []

        def runner(command, **kwargs):
            calls.append(command[1:])
            answer = "unix:///var/run/docker.sock" if command[1] == "context" else "ok"
            return SimpleNamespace(returncode=0, stdout=answer, stderr="")

        checks = check(environ={}, which=lambda name: "/usr/bin/docker", runner=runner)
        self.assertTrue(all(checks.values()))
        self.assertEqual([item[0] for item in calls], ["context", "compose", "info"])

    def test_remote_override_refuses_before_docker_call(self):
        def never(*args, **kwargs):
            self.fail("remote override must prevent a Docker probe")

        checks = check(environ={"DOCKER_HOST": "tcp://example.invalid:2375"},
                       which=lambda name: "/usr/bin/docker", runner=never)
        self.assertFalse(checks["local_unix_context"])

    def test_remote_context_never_probes_daemon(self):
        calls = []

        def runner(command, **kwargs):
            calls.append(command[1])
            return SimpleNamespace(returncode=0, stdout="ssh://example.invalid", stderr="")

        checks = check(environ={}, which=lambda name: "/usr/bin/docker", runner=runner)
        self.assertFalse(checks["local_daemon_readable"])
        self.assertEqual(calls, ["context"])


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.area = Path(self.tmp.name)
        self.source = self.area / "checkout"
        self.source.mkdir()
        self.destination = self.area / "private-copy"
        worksheet = self.source / "hosts/server-01/assembly.example.json"
        worksheet.parent.mkdir(parents=True)
        shutil.copyfile(Path(__file__).with_name("assembly.example.json"), worksheet)
        for guide, _ in MODULES.values():
            path = self.source / guide
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Fictional module guide\n", encoding="utf-8")
        for project, names in FILES.items():
            base = self.source / SOURCES[project]
            for name in names:
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if name == ".env.example":
                    content = "".join(key + "=\n" for key in BLANK_INPUTS[project])
                else:
                    content = "fictional fixture\n"
                path.write_text(content, encoding="utf-8")

    def test_additive_copy_keeps_private_inputs_blank_and_rejects_overwrite(self):
        self.assertEqual(prepare(self.source, self.destination), [])
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
        for project in FILES:
            env = self.destination / project / ".env"
            self.assertEqual(env.stat().st_mode & 0o777, 0o600)
            self.assertEqual(env.read_text(), (self.destination / project / ".env.example").read_text())
        self.assertEqual((self.destination / "metrics/.secrets").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.destination / "acceptance.json").stat().st_mode & 0o777, 0o600)
        self.assertIn('"NOT_RUN"', (self.destination / "acceptance.json").read_text())
        (self.destination / "ai/.env").write_text("private local choice\n")
        self.assertIn("new_absolute_destination_required", prepare(self.source, self.destination))
        self.assertEqual((self.destination / "ai/.env").read_text(), "private local choice\n")

    def test_rejects_linked_fixture_before_creating_destination(self):
        item = self.source / SOURCES["ai"] / "compose.yaml"
        item.unlink()
        item.symlink_to(self.area / "outside.txt")
        self.assertIn("reviewed_fixture_missing_or_linked", prepare(self.source, self.destination))
        self.assertFalse(self.destination.exists())

    def test_rejects_linked_directory_even_when_target_stays_in_checkout(self):
        base = self.source / SOURCES["metrics"]
        dashboard = base / "dashboards"
        dashboard.rename(base / "other-dashboards")
        dashboard.symlink_to("other-dashboards")
        self.assertIn("reviewed_fixture_missing_or_linked", prepare(self.source, self.destination))
        self.assertFalse(self.destination.exists())

    def test_rejects_filled_public_secret_template(self):
        template = self.source / SOURCES["ai"] / ".env.example"
        template.write_text(template.read_text().replace("WEBUI_SECRET_KEY=",
                                                        "WEBUI_SECRET_KEY=filled"))
        self.assertIn("public_template_must_keep_private_inputs_blank",
                      prepare(self.source, self.destination))
        self.assertFalse(self.destination.exists())

    def test_refuses_destination_inside_public_checkout(self):
        self.assertIn("destination_must_be_outside_checkout",
                      prepare(self.source, self.source / "private-copy"))
        self.assertFalse((self.source / "private-copy").exists())


class PublishedCheckoutTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / SOURCES["catalog"] / "config/services.yaml").is_file(),
                         "partial review copy; complete checkout tested in CI")
    def test_complete_public_checkout_prepares_isolated_private_copy(self):
        with tempfile.TemporaryDirectory() as area:
            destination = Path(area) / "private-copy"
            self.assertEqual(prepare(ROOT, destination), [])
            for project, names in FILES.items():
                for name in names:
                    self.assertTrue((destination / project / name).is_file())


if __name__ == "__main__":
    unittest.main()
