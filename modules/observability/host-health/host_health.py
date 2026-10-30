#!/usr/bin/env python3
"""Opt-in Linux host snapshot. Only bounded labels reach stdout."""

import argparse
import json
import os
from pathlib import Path
import time


CPU_LIMIT_PERCENT = 90
MIN_AVAILABLE_PERCENT = 10
LABEL_OK = "WITHIN_EXAMPLE_BOUND"
LABEL_REVIEW = "REVIEW"
LABEL_UNKNOWN = "UNKNOWN"


def cpu_counters(text):
    line = next((line for line in text.splitlines() if line.startswith("cpu ")), None)
    if line is None:
        raise ValueError("cpu counters unavailable")
    parts = line.split()
    if len(parts) < 9:
        raise ValueError("cpu counter shape")
    values = tuple(int(value) for value in parts[1:9])
    if any(value < 0 for value in values):
        raise ValueError("cpu counter range")
    return values


def memory_counts(text):
    values = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] in ("MemTotal:", "MemAvailable:") and parts[2] == "kB":
            values[parts[0]] = int(parts[1])
    total = values.get("MemTotal:")
    available = values.get("MemAvailable:")
    if total is None or available is None or total <= 0 or not 0 <= available <= total:
        raise ValueError("memory counter range")
    return total, available


def percentage(numerator, denominator):
    if not all(type(value) is int for value in (numerator, denominator)):
        raise ValueError("counter type")
    if denominator <= 0 or not 0 <= numerator <= denominator:
        raise ValueError("counter range")
    return 100 * numerator / denominator


def evaluate(first, second, memory, root_blocks):
    if len(first) != 8 or len(second) != 8:
        raise ValueError("cpu counter length")
    deltas = [end - start for start, end in zip(first, second)]
    if any(delta < 0 for delta in deltas):
        raise ValueError("cpu counter moved backward")
    total = sum(deltas)
    idle = deltas[3] + deltas[4]
    busy_percent = 100 - percentage(idle, total)
    memory_available = percentage(memory[1], memory[0])
    root_available = percentage(root_blocks[1], root_blocks[0])
    return {
        "cpu": LABEL_OK if busy_percent <= CPU_LIMIT_PERCENT else LABEL_REVIEW,
        "memory": LABEL_OK if memory_available >= MIN_AVAILABLE_PERCENT else LABEL_REVIEW,
        "root_filesystem": LABEL_OK if root_available >= MIN_AVAILABLE_PERCENT else LABEL_REVIEW,
    }


def live_sample():
    first = cpu_counters(Path("/proc/stat").read_text(encoding="ascii"))
    time.sleep(1)
    second = cpu_counters(Path("/proc/stat").read_text(encoding="ascii"))
    memory = memory_counts(Path("/proc/meminfo").read_text(encoding="ascii"))
    fs = os.statvfs("/")
    return evaluate(first, second, memory, (fs.f_blocks, fs.f_bavail))


def fictional_sample():
    data = json.loads(Path(__file__).with_name("fictional.example.json").read_text(encoding="utf-8"))
    if set(data) != {"scope", "cpu_first", "cpu_second", "memory_total_kib", "memory_available_kib", "root_blocks", "root_available_blocks"} or data["scope"] != "fictional":
        raise ValueError("fictional fixture shape")
    return evaluate(data["cpu_first"], data["cpu_second"],
                    (data["memory_total_kib"], data["memory_available_kib"]),
                    (data["root_blocks"], data["root_available_blocks"]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="One-shot local Linux host-health labels")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--fictional", action="store_true", help="use the checked-in invented fixture")
    choice.add_argument("--live", action="store_true", help="read this Linux host once; print labels only")
    args = parser.parse_args(argv)
    try:
        labels = fictional_sample() if args.fictional else live_sample()
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        labels = {name: LABEL_UNKNOWN for name in ("cpu", "memory", "root_filesystem")}
    output = {"scope": "fictional" if args.fictional else "local_one_shot",
              "result": LABEL_UNKNOWN if LABEL_UNKNOWN in labels.values() else
                        LABEL_REVIEW if LABEL_REVIEW in labels.values() else LABEL_OK,
              "checks": labels, "network_requests": 0, "records_written": 0}
    print(json.dumps(output, sort_keys=True))
    return 0 if output["result"] == LABEL_OK else 2 if output["result"] == LABEL_UNKNOWN else 1


if __name__ == "__main__":
    raise SystemExit(main())
