#!/usr/bin/env python3
"""Bounded private Linux trend collection and static fictional/private dashboard."""

import argparse
from datetime import datetime, timezone
import html
import json
import math
import os
from pathlib import Path
import re
import stat
import time


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).with_name("trends.example.jsonl").resolve()
MAX_SAMPLES = 120
MAX_INPUT_BYTES = 64_000
METRICS = ("cpu_busy_pct", "memory_available_pct", "root_available_pct")


def percent(part, whole):
    if type(part) is not int or type(whole) is not int or whole <= 0 or not 0 <= part <= whole:
        raise ValueError("counter range")
    return round(100 * part / whole, 1)


def cpu_values(text):
    line = next((line for line in text.splitlines() if line.startswith("cpu ")), None)
    if line is None:
        raise ValueError("cpu unavailable")
    parts = line.split()
    if len(parts) < 9:
        raise ValueError("cpu shape")
    values = tuple(int(part) for part in parts[1:9])
    if any(value < 0 for value in values):
        raise ValueError("cpu range")
    return values


def memory_values(text):
    found = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] in ("MemTotal:", "MemAvailable:") and parts[2] == "kB":
            found[parts[0]] = int(parts[1])
    if set(found) != {"MemTotal:", "MemAvailable:"}:
        raise ValueError("memory unavailable")
    return found["MemTotal:"], found["MemAvailable:"]


def sample_once():
    first = cpu_values(Path("/proc/stat").read_text(encoding="ascii"))
    time.sleep(1)
    second = cpu_values(Path("/proc/stat").read_text(encoding="ascii"))
    deltas = [end - start for start, end in zip(first, second)]
    if any(delta < 0 for delta in deltas):
        raise ValueError("cpu counter moved backward")
    idle = deltas[3] + deltas[4]
    busy = 100 - percent(idle, sum(deltas))
    total_mem, available_mem = memory_values(Path("/proc/meminfo").read_text(encoding="ascii"))
    fs = os.statvfs("/")
    return tuple(round(value, 1) for value in
                 (busy, percent(available_mem, total_mem), percent(fs.f_bavail, fs.f_blocks)))


def private_new_path(value):
    requested = Path(value)
    if not requested.is_absolute() or requested.name in ("", ".", ".."):
        raise ValueError("absolute new path required")
    parent = requested.parent.resolve(strict=True)
    if parent == ROOT or ROOT in parent.parents:
        raise ValueError("repository output refused")
    info = parent.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("private owner directory required")
    result = parent / requested.name
    if result.exists() or result.is_symlink():
        raise ValueError("output already exists")
    return result


def write_line(stream, value):
    stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def valid_metrics(values):
    if len(values) != 3 or any(type(value) not in (int, float) or
                               not math.isfinite(value) or not 0 <= value <= 100 for value in values):
        raise ValueError("metric range")


def collect(output_dir, count, interval, sample_fn=sample_once, pause=time.sleep,
            now_fn=lambda: datetime.now(timezone.utc)):
    if type(count) is not int or not 2 <= count <= MAX_SAMPLES or type(interval) is not int or not 1 <= interval <= 3600:
        raise ValueError("bounded run required")
    directory = private_new_path(output_dir)
    os.mkdir(directory, 0o700)
    os.chmod(directory, 0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(directory / "samples.jsonl", flags, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        write_line(stream, {"kind": "header", "schema_version": 1, "scope": "private_local",
                            "planned_samples": count, "interval_seconds": interval})
        for index in range(1, count + 1):
            values = sample_fn()
            valid_metrics(values)
            stamp = now_fn().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            write_line(stream, {"kind": "sample", "index": index, "observed_at_utc": stamp,
                                **dict(zip(METRICS, values))})
            if index < count:
                pause(interval)
        write_line(stream, {"kind": "complete", "samples": count})
    return count


def parse_series(data):
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("series too large")
    lines = data.decode("utf-8").splitlines()
    if not 4 <= len(lines) <= MAX_SAMPLES + 2 or any(not line for line in lines):
        raise ValueError("series length")
    rows = [json.loads(line) for line in lines]
    header, complete = rows[0], rows[-1]
    if (type(header) is not dict or set(header) != {"kind", "schema_version", "scope", "planned_samples", "interval_seconds"}
            or header["kind"] != "header" or header["schema_version"] != 1
            or header["scope"] not in ("fictional", "private_local")
            or type(header["planned_samples"]) is not int or not 2 <= header["planned_samples"] <= MAX_SAMPLES
            or type(header["interval_seconds"]) is not int or not 1 <= header["interval_seconds"] <= 3600):
        raise ValueError("header shape")
    samples = rows[1:-1]
    if (type(complete) is not dict or set(complete) != {"kind", "samples"}
            or complete["kind"] != "complete" or type(complete["samples"]) is not int
            or complete["samples"] != header["planned_samples"] or len(samples) != complete["samples"]):
        raise ValueError("incomplete series")
    previous = None
    for index, row in enumerate(samples, 1):
        if type(row) is not dict or set(row) != {"kind", "index", "observed_at_utc", *METRICS} or row["kind"] != "sample" or type(row["index"]) is not int or row["index"] != index:
            raise ValueError("sample shape")
        stamp = row["observed_at_utc"]
        if type(stamp) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp):
            raise ValueError("timestamp shape")
        parsed = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if previous is not None and parsed <= previous:
            raise ValueError("time order")
        previous = parsed
        valid_metrics(tuple(row[name] for name in METRICS))
    return header["scope"], samples


def load_series(path):
    requested = Path(path)
    if requested.is_symlink():
        raise ValueError("symlink refused")
    resolved = requested.resolve(strict=True)
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_INPUT_BYTES:
        raise ValueError("input type")
    if resolved != FIXTURE:
        if resolved == ROOT or ROOT in resolved.parents:
            raise ValueError("unreviewed repository input")
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("private input required")
    data = resolved.read_bytes()
    scope, samples = parse_series(data)
    if (resolved == FIXTURE) != (scope == "fictional"):
        raise ValueError("scope mismatch")
    return scope, samples


def render_html(scope, samples):
    fictional = scope == "fictional"
    title = "Fictional OUTLANDS host trend" if fictional else "Private local host trend"
    colors = ("#e54b4b", "#60c7df", "#f3c46a")
    names = ("CPU busy", "Memory available", "Root available")
    paths = []
    for metric, color in zip(METRICS, colors):
        points = []
        for index, row in enumerate(samples):
            x = 55 + (650 * index / (len(samples) - 1))
            y = 220 - 1.7 * row[metric]
            points.append(f"{x:.1f},{y:.1f}")
        paths.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="3"/>')
    body_rows = "\n".join(
        "<tr><td>" + html.escape(row["observed_at_utc"]) + "</td>" +
        "".join(f"<td>{row[metric]:.1f}%</td>" for metric in METRICS) + "</tr>"
        for row in samples)
    legend = "".join(f'<span style="color:{color}">● {name}</span>' for color, name in zip(colors, names))
    notice = "INVENTED DATA — public example" if fictional else "PRIVATE LOCAL DATA — keep this file private"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{title}</title>
<style>body{{background:#101318;color:#edf0f3;font:16px system-ui;margin:0 auto;max-width:950px;padding:2rem}}h1{{color:#fff}}.notice{{color:#f3c46a;font-weight:700}}.legend{{display:flex;gap:1.5rem;flex-wrap:wrap}}svg{{width:100%;height:auto;background:#1b222c;border:1px solid #46505e}}table{{border-collapse:collapse;width:100%}}th,td{{border-bottom:1px solid #46505e;padding:.5rem;text-align:left}}th{{color:#f3c46a}}p{{line-height:1.5}}</style></head>
<body><p class="notice">{notice}</p><h1>{title}</h1><p>Bounded local samples: {len(samples)}. Percentages are observations, not alert policy or proof of complete host health.</p>
<div class="legend">{legend}</div><svg viewBox="0 0 760 250" role="img" aria-label="CPU busy, memory available, and root filesystem available percentages over sample order"><path d="M55 50V220H705" fill="none" stroke="#8994a3"/><text x="10" y="55" fill="#edf0f3">100%</text><text x="25" y="220" fill="#edf0f3">0%</text>{''.join(paths)}</svg>
<h2>Samples</h2><table><thead><tr><th>UTC</th><th>CPU busy</th><th>Memory available</th><th>Root available</th></tr></thead><tbody>{body_rows}</tbody></table>
<p>Root filesystem only. No host name, mount list, Docker state, GPU, process names, or backup state is collected.</p></body></html>
'''


def render(input_path, output_path):
    scope, samples = load_series(input_path)
    target = private_new_path(output_path)
    content = render_html(scope, samples).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return scope, len(samples)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Private bounded host trends and static dashboard")
    commands = parser.add_subparsers(dest="command", required=True)
    collect_cmd = commands.add_parser("collect")
    collect_cmd.add_argument("--output-dir", required=True)
    collect_cmd.add_argument("--samples", required=True, type=int)
    collect_cmd.add_argument("--interval-seconds", required=True, type=int)
    render_cmd = commands.add_parser("render")
    render_cmd.add_argument("--input", required=True)
    render_cmd.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            count = collect(args.output_dir, args.samples, args.interval_seconds)
            result = {"result": "COMPLETE", "samples": count, "scope": "private_local"}
        else:
            scope, count = render(args.input, args.output)
            result = {"result": "CREATED", "samples": count, "scope": scope}
        code = 0
    except KeyboardInterrupt:
        result, code = {"result": "REVIEW", "reason": "interrupted"}, 2
    except Exception:
        result, code = {"result": "REVIEW", "reason": "input_or_sample_error"}, 2
    result.update({"network_requests": 0, "automatic_cleanup": False})
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
