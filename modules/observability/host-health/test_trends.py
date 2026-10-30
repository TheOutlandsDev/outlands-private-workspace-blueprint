"""Fictional and mocked trend checks; no actual host sampling."""

from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stdout
from types import SimpleNamespace

import trends


def rows():
    return [json.loads(line) for line in trends.FIXTURE.read_text(encoding="utf-8").splitlines()]


def encoded(items):
    return ("\n".join(json.dumps(item) for item in items) + "\n").encode("utf-8")


class TrendTests(unittest.TestCase):
    def test_fictional_fixture_and_static_dashboard(self):
        scope, samples = trends.load_series(trends.FIXTURE)
        page = trends.render_html(scope, samples)
        self.assertEqual((scope, len(samples)), ("fictional", 4))
        self.assertIn("INVENTED DATA", page)
        self.assertIn("<svg", page)
        self.assertEqual(page.count("<polyline"), 3)
        self.assertEqual(page.count("<tr>"), 5)
        self.assertNotIn("<script", page.lower())
        self.assertNotIn("http://", page.lower())
        self.assertNotIn("https://", page.lower())
        self.assertNotIn("docker.sock", page.lower())
        self.assertEqual(page, trends.FIXTURE.with_name("dashboard.example.html").read_text(encoding="utf-8"))

    def test_strict_series_rejects_extra_label_and_incomplete_run(self):
        series = rows()
        series[1]["hostname"] = "fictional-but-forbidden"
        with self.assertRaises(ValueError):
            trends.parse_series(encoded(series))
        series = rows()[:-1]
        with self.assertRaises(ValueError):
            trends.parse_series(encoded(series))

    def test_strict_series_rejects_bad_value_and_time(self):
        series = rows()
        series[1]["cpu_busy_pct"] = float("nan")
        with self.assertRaises(ValueError):
            trends.parse_series(encoded(series))
        series = rows()
        series[2]["observed_at_utc"] = "<img src=x>"
        with self.assertRaises(ValueError):
            trends.parse_series(encoded(series))
        series = rows()
        series[2]["observed_at_utc"] = series[1]["observed_at_utc"]
        with self.assertRaises(ValueError):
            trends.parse_series(encoded(series))

    def test_mocked_kernel_sample(self):
        cpu_first = "cpu 100 0 20 800 30 0 0 0\n"
        cpu_second = "cpu 110 0 25 885 30 0 0 0\n"
        memory = "MemTotal: 1000 kB\nMemAvailable: 600 kB\n"
        with mock.patch.object(Path, "read_text", side_effect=[cpu_first, cpu_second, memory]), \
             mock.patch.object(trends.time, "sleep") as pause, \
             mock.patch.object(trends.os, "statvfs", return_value=SimpleNamespace(f_blocks=1000, f_bavail=400)):
            result = trends.sample_once()
        self.assertEqual(result, (15.0, 60.0, 40.0))
        pause.assert_called_once_with(1)

    def test_collect_private_new_directory_with_complete_marker(self):
        with tempfile.TemporaryDirectory() as parent:
            start = datetime(2020, 1, 1, tzinfo=timezone.utc)
            times = iter((start, start + timedelta(minutes=1)))
            directory = Path(parent) / "run-001"
            count = trends.collect(str(directory), 2, 1, sample_fn=lambda: (15.0, 60.0, 40.0),
                                   pause=lambda seconds: None, now_fn=lambda: next(times))
            self.assertEqual(count, 2)
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            source = directory / "samples.jsonl"
            self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o600)
            scope, samples = trends.load_series(source)
            self.assertEqual((scope, len(samples)), ("private_local", 2))
            with self.assertRaises(ValueError):
                trends.collect(str(directory), 2, 1, sample_fn=lambda: None)

    def test_failure_preserves_partial_series_without_completion(self):
        with tempfile.TemporaryDirectory() as parent:
            calls = iter(((15.0, 60.0, 40.0), OSError("private device detail")))
            def sample():
                value = next(calls)
                if isinstance(value, OSError):
                    raise value
                return value
            directory = Path(parent) / "interrupted"
            with self.assertRaises(OSError):
                trends.collect(str(directory), 2, 1, sample_fn=sample, pause=lambda seconds: None,
                               now_fn=lambda: datetime(2020, 1, 1, tzinfo=timezone.utc))
            source = directory / "samples.jsonl"
            self.assertTrue(source.exists())
            self.assertNotIn('"kind":"complete"', source.read_text(encoding="utf-8"))
            with self.assertRaises(ValueError):
                trends.load_series(source)

    def test_render_writes_private_file_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "fictional.html"
            self.assertEqual(trends.render(str(trends.FIXTURE), str(output)), ("fictional", 4))
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            original = output.read_bytes()
            with self.assertRaises(ValueError):
                trends.render(str(trends.FIXTURE), str(output))
            self.assertEqual(output.read_bytes(), original)

    def test_repo_output_and_public_private_input_refused(self):
        with self.assertRaises(ValueError):
            trends.private_new_path(str(trends.ROOT / "should-not-be-created"))
        with tempfile.TemporaryDirectory() as parent:
            public_copy = Path(parent) / "public.jsonl"
            public_copy.write_bytes(trends.FIXTURE.read_bytes())
            public_copy.chmod(0o644)
            with self.assertRaises(ValueError):
                trends.load_series(public_copy)

    def test_public_parent_and_symlink_input_refused(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = Path(parent)
            directory.chmod(0o755)
            with self.assertRaises(ValueError):
                trends.private_new_path(str(directory / "new-report.html"))
            directory.chmod(0o700)
            link = directory / "linked-series.jsonl"
            link.symlink_to(trends.FIXTURE)
            with self.assertRaises(ValueError):
                trends.load_series(link)

    def test_cli_stdout_is_bounded(self):
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "preview.html"
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = trends.main(["render", "--input", str(trends.FIXTURE), "--output", str(output)])
            self.assertEqual(code, 0)
            result = json.loads(stream.getvalue())
            self.assertEqual(set(result), {"result", "samples", "scope", "network_requests", "automatic_cleanup"})
            self.assertNotIn(str(parent), stream.getvalue())
            self.assertNotIn("22.0", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
