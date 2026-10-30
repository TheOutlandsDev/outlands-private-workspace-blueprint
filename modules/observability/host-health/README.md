# server-01 host health: local snapshot and bounded trends

This optional Linux module gives a reader a **one-shot** CPU, available-memory, and root-filesystem check. A separate bounded foreground command can collect a private series and render a static HTML dashboard. Both use Python's standard library. Neither opens a listening port, sends a network request, starts a service, or uses Docker or its socket. The one-shot command prints fixed labels and stores no reading; the trends command writes actual percentages and times only in a new reader-owned private directory outside this repository. `server-01` is a fictional host role; the public files contain no operator readings, hostnames, device IDs, mount lists, or paths to private data.

This is separate from the [fictional Prometheus/Grafana module](../synthetic-metrics/README.md). It does not feed that dashboard, monitor the AI project, or install an exporter. Run a live check directly on a reader-owned Linux host only after reviewing its source. Running it inside a container reports that container's view, which may differ from the host.

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

## 3. Preview invented trends

The checked-in [fictional series](trends.example.jsonl) contains four invented samples. Its [static example dashboard](dashboard.example.html) is generated from those rows and contains no script, external asset, or real host data. The source tests verify the page matches the fixture exactly. To generate a separate local preview from a downloaded checkout, choose a **new** private directory outside the repository:

```sh
umask 077
mkdir -m 700 "$HOME/outlands-trends-private"
python3 -I -B modules/observability/host-health/trends.py render \
  --input modules/observability/host-health/trends.example.jsonl \
  --output "$HOME/outlands-trends-private/fictional.html"
```

The renderer requires an owner-controlled private output directory, refuses an existing file, and writes mode 0600. Open that local HTML file in a browser of your choice. It does not start a web server or publish a route.

## 4. Collect and view a private bounded window only if chosen

After reviewing `trends.py` on the intended Linux host, choose a new run directory under the private parent made above. This example takes 12 samples; each samples aggregate CPU counters across one second, then waits 60 seconds before the next sample. The allowed range is 2–120 samples and 1–3600 seconds between samples. The command runs in the foreground and ends by itself.

```sh
python3 -I -B modules/observability/host-health/trends.py collect \
  --output-dir "$HOME/outlands-trends-private/run-001" \
  --samples 12 --interval-seconds 60
python3 -I -B modules/observability/host-health/trends.py render \
  --input "$HOME/outlands-trends-private/run-001/samples.jsonl" \
  --output "$HOME/outlands-trends-private/run-001/dashboard.html"
```

The collector creates a new mode-0700 run directory and mode-0600 JSONL file. Rows contain only UTC time and three percentages; they contain no hostname, process, mount name, Docker metadata, or account label. A final completion row is written only after every requested sample succeeds. On interruption or failure, the partial file remains for private inspection and the renderer refuses to call it complete. The CLI prints only a fixed result and sample count, never a reading or path. The dashboard is a mode-0600, self-contained HTML file with no script or external resource; its **real** percentages and times remain private. Do not commit either live file or share it through an unreviewed route. There is no automatic retention or cleanup: choose storage, access, and deletion in your own private policy.

This is a bounded trend window, not continuous alerting. It covers only the root filesystem and these three aggregate measurements. It does not prove disk integrity, other-mount capacity, application health, GPU use, backups, or availability. A reader may start another window later in a different new directory after reviewing resource impact; this example installs no timer or background process.

| Trend acceptance check on a reader-owned host | Result |
| --- | --- |
| Fictional dashboard renders from the invented fixture | NOT RUN |
| New private directory and file modes confirmed | NOT RUN |
| Complete live series contains only approved fields | NOT RUN |
| Static live dashboard opens locally without external requests | NOT RUN |
| Retention and access choices recorded privately | NOT RUN |

## 5. Operate and reverse

There is no daemon, Compose project, account, port, volume, or scheduled job to install. Do not add a timer, remote route, metrics endpoint, log, or exporter merely by copying this example. For a new version, inspect the diff and repeat the fictional checks before choosing another live run. To stop using it, run no further command. Preserve any private series and dashboard according to the reader's own retention and recovery decisions; this repository provides no deletion or backup automation. Keep those decisions outside this public repository.

Repository checks establish only the fictional and mocked behavior. They cannot prove a reader's actual resource condition, storage coverage, application health, GPU capacity, or a deployed monitoring pipeline. Upstream kernel and Python references checked 2026-10-30.
