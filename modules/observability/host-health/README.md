# server-01 host health: opt-in local snapshot

This optional Linux module gives a reader a **one-shot** CPU, available-memory, and root-filesystem check. It uses Python's standard library and prints only fixed result labels. It opens no listening port, sends no network request, starts no service, stores no reading, and does not use Docker or its socket. `server-01` is a fictional host role; this repository contains no operator readings, hostnames, device IDs, mount lists, or paths to private data.

This is separate from the [fictional Prometheus/Grafana module](../synthetic-metrics/README.md). It does not feed that dashboard, monitor the AI project, or install an exporter. Run it directly on a reader-owned Linux host only after reviewing its source and deciding that a local snapshot is appropriate. Running it inside a container reports that container's view, which may differ from the host.

## What it observes

| Check | Source and example bound | Printed result |
| --- | --- | --- |
| CPU | Two aggregate `/proc/stat` counter samples one second apart; busy time at most 90% | Fixed label only |
| Available memory | `/proc/meminfo` `MemAvailable` divided by `MemTotal`; at least 10% | Fixed label only |
| Root filesystem | `os.statvfs` on `/`; blocks available to an unprivileged user divided by total blocks; at least 10% | Fixed label only |

The bounds are **teaching examples**, not a capacity policy or a health certificate. A one-second CPU sample can miss bursts; `MemAvailable` is a kernel estimate; the root-filesystem result says nothing about other mounts, volume recovery, disk errors, or backup readiness. Counter regressions, missing fields, and read failures return `UNKNOWN`, never a healthy label. The [Linux `/proc` documentation](https://docs.kernel.org/filesystems/proc.html) defines the counter fields and memory estimate; [Python's `statvfs` reference](https://docs.python.org/3/library/os.html#os.statvfs) defines the block fields.

## 1. Inspect the fictional example

From a downloaded repository copy, use Python 3.9 or later:

```sh
python3 -I -B modules/observability/host-health/host_health.py --fictional
python3 -I -B -m unittest discover -s modules/observability/host-health -p 'test_*.py'
```

The checked-in `fictional.example.json` has invented counters and no machine identity. The tests use that fixture and mocked reads; they do not sample the runner's host. Keep this directory free of filled results, exported metrics, screenshots, or private configuration.

## 2. Run one local snapshot only if chosen

On the intended Linux host, as an ordinary user, review the source and run:

```sh
python3 -I -B modules/observability/host-health/host_health.py --live
```

The output has a fixed `scope`, three named check labels, `network_requests: 0`, and `records_written: 0`. It contains no numeric reading or filesystem path. `WITHIN_EXAMPLE_BOUND` means only that this one sample met the three example thresholds; `REVIEW` means at least one threshold was crossed; `UNKNOWN` means the sample could not be evaluated. Exit status is 0, 1, or 2 respectively. Do not paste even bounded live status into a public issue unless you intentionally choose to disclose it.

| Reader's acceptance check | Result |
| --- | --- |
| Source and intended Linux execution context reviewed | NOT RUN |
| Fictional fixture behaves as documented | NOT RUN |
| Local live snapshot completed without an unexpected error | NOT RUN |
| Any REVIEW or UNKNOWN result investigated privately | NOT RUN |
| Other filesystems and application health checked separately if needed | NOT RUN |

## 3. Operate and reverse

There is no daemon, Compose project, account, port, volume, or scheduled job to install. A run ends after the one-second sample. Do not add a timer, remote route, metrics endpoint, log, or exporter merely by copying this example. For a new version, inspect the diff and repeat the fictional check before choosing another live run. To stop using it, run no further command; no service or data needs deletion. The module has no persistent state to back up or restore. Keep any operator notes and recovery plans private, with no backup destination or provider in this repository.

Repository checks establish only the fictional and mocked behavior. They cannot prove a reader's actual resource condition, storage coverage, application health, GPU capacity, or a deployed monitoring pipeline. Upstream kernel and Python references checked 2026-10-30.
