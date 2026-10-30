"""Fictional and mocked checks; never read the test runner's host."""

import contextlib
import io
import json
import unittest
from unittest import mock

import host_health as health


FIRST = (100, 0, 20, 800, 30, 0, 0, 0)
SECOND = (110, 0, 25, 885, 30, 0, 0, 0)


class HostHealthTests(unittest.TestCase):
    def test_fictional_fixture_is_bounded(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = health.main(["--fictional"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["scope"], "fictional")
        self.assertEqual(result["result"], health.LABEL_OK)
        self.assertEqual(set(result["checks"]), {"cpu", "memory", "root_filesystem"})
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["records_written"], 0)

    def test_each_example_threshold_can_request_review(self):
        cases = (
            ((100, 0, 20, 800, 30, 0, 0, 0), (195, 0, 20, 805, 30, 0, 0, 0), (100, 50), (100, 50), "cpu"),
            (FIRST, SECOND, (100, 9), (100, 50), "memory"),
            (FIRST, SECOND, (100, 50), (100, 9), "root_filesystem"),
        )
        for first, second, mem, fs, expected in cases:
            with self.subTest(expected=expected):
                labels = health.evaluate(first, second, mem, fs)
                self.assertEqual(labels[expected], health.LABEL_REVIEW)

    def test_missing_or_backwards_counters_are_unknown(self):
        with self.assertRaises(ValueError):
            health.evaluate(FIRST, FIRST, (100, 50), (100, 50))
        with self.assertRaises(ValueError):
            health.evaluate(SECOND, FIRST, (100, 50), (100, 50))
        with self.assertRaises(ValueError):
            health.evaluate(FIRST, SECOND, (100, 101), (100, 50))
        with self.assertRaises(ValueError):
            health.evaluate(FIRST, SECOND, (100, 50), (0, 0))

    def test_proc_parsers_require_expected_fields(self):
        self.assertEqual(health.cpu_counters("cpu 1 2 3 4 5 6 7 8 9\ncpu0 1 2"), (1, 2, 3, 4, 5, 6, 7, 8))
        self.assertEqual(health.memory_counts("MemTotal: 100 kB\nMemAvailable: 25 kB\n"), (100, 25))
        with self.assertRaises(ValueError):
            health.cpu_counters("cpu0 1 2 3 4 5 6 7 8")
        with self.assertRaises(ValueError):
            health.memory_counts("MemTotal: 100 kB\n")

    def test_live_cli_prints_only_fixed_labels(self):
        output = io.StringIO()
        with mock.patch.object(health, "live_sample", return_value={"cpu": health.LABEL_REVIEW,
                    "memory": health.LABEL_OK, "root_filesystem": health.LABEL_OK}), contextlib.redirect_stdout(output):
            code = health.main(["--live"])
        self.assertEqual(code, 1)
        self.assertEqual(set(json.loads(output.getvalue())), {"scope", "result", "checks", "network_requests", "records_written"})
        self.assertNotIn("/", output.getvalue())

    def test_live_error_suppresses_host_exception(self):
        output = io.StringIO()
        with mock.patch.object(health, "live_sample", side_effect=OSError("private device label")), contextlib.redirect_stdout(output):
            code = health.main(["--live"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["result"], health.LABEL_UNKNOWN)
        self.assertNotIn("private device label", output.getvalue())


if __name__ == "__main__":
    unittest.main()
