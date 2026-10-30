# server-01 observability: synthetic metrics

This optional module gives readers a **fictional** Prometheus target and a small Grafana dashboard. It demonstrates scrape availability, source observation age, and a sample value without collecting host metrics. There is no Node Exporter, cAdvisor, Docker socket, real target list, hostname, account, route, or operator data in this example. `server-01` is a role label, not a live inventory entry.

The [host foundation](../../foundation/docker-host/README.md) comes first. This module uses its own Compose project and does not depend on the [AI module](../../ai/ollama-open-webui/README.md) or [private entry module](../../access/private-entry/README.md). Prometheus and Grafana bind only to host loopback. The fixture is reachable only on the Compose network. Do not publish Prometheus directly or add a remote route to either UI without a separate access review.

## What the synthetic modes mean

| Mode | Fixture response | Expected Prometheus/Grafana observation |
| --- | --- | --- |
| `fresh` | HTTP 200; observation time is current | `up=1`; source age near zero; sample value 7 |
| `stale` | HTTP 200; observation time is ten minutes old | `up=1`; source age roughly 600 seconds; sample value 7 |
| `unavailable` | HTTP 503; no sample metrics | `up=0`; source metrics disappear after Prometheus staleness handling |

`up=1` proves a scrape succeeded, not that source data is fresh. A missing time series is **UNKNOWN**, not a measured zero. The dashboard's source-age threshold is a teaching value, not an alert policy for a real service. Prometheus [configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/) and [exposition format](https://prometheus.io/docs/instrumenting/exposition_formats/) define the underlying concepts.

## 1. Prepare an isolated test project

Use a new staging installation with Docker Engine and Compose. Review current upstream [Prometheus installation](https://prometheus.io/docs/prometheus/latest/installation/) and [Grafana Docker](https://grafana.com/docs/grafana/latest/setup-grafana/configure-docker/) documentation, including image provenance and licenses. Choose reviewed immutable image digests for Prometheus, Grafana OSS, and a Python image for your architecture. The repository does not select versions for your host. Check the [Grafana provisioning guide](https://grafana.com/docs/grafana/latest/administration/provisioning/) against your selected release before using the dashboard files.

From this module directory in a private test copy:

```sh
umask 077
cp .env.example .env
mkdir -m 700 .secrets
openssl rand -hex 32 > .secrets/grafana-admin-password
chmod 600 .env .secrets/grafana-admin-password
```

Fill the three image references in `.env` with reviewed `@sha256:` digests. The public file has blank values. The `.secrets` directory and `.env` are ignored by Git, and the source screen rejects a checked-in secrets directory. Do not publish the generated password, `.env`, Compose output, Grafana database, Prometheus data, dashboard exports from a real instance, or screenshots containing labels. Grafana reads the password through a Compose secret file. Keep the same secret and state for a controlled update; do not treat the sample password file as a recovery design.

## 2. Resolve and start only this example

```sh
python3 -I -B check_example.py
docker compose --env-file .env -f compose.yaml config --quiet
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
```

The first command reads only repository files. `config --quiet` resolves the model without starting containers. `up -d` may pull images and creates a test network and named data volumes. Inspect `ps` before opening the UIs: Prometheus should publish only on `127.0.0.1:9090`, Grafana only on `127.0.0.1:3002`, and the fixture on no host port. Choose unused local ports privately if the example values conflict. Do not attach this project to a real metrics network or add real scrape targets to the public file.

Open `http://127.0.0.1:3002/` on the test host. Sign in with the Grafana administrator account and the password stored privately in `.secrets/grafana-admin-password`; change and manage credentials according to the selected Grafana release. Confirm anonymous access and public signup are disabled. The provisioned data source points only to the internal Prometheus service, and the dashboard is named **Synthetic source states**. Inspect the three panels in the native UI before trusting them; JSON structure and Compose resolution alone do not prove the dashboard renders correctly.

## 3. Exercise fresh, stale, and unavailable states

Start with `DEMO_MODE=fresh`. The dashboard should show a successful scrape, a recent observation age, and fictional value 7. In the private `.env`, change `DEMO_MODE` to `stale`, then recreate only the fixture service using your reviewed Compose command. After the next scrape, check that the target remains up while the observation age rises above the red example threshold. Change to `unavailable` and recreate the fixture again: the target should report `up=0`, while source metrics become absent. Restore `fresh` and verify recovery. Do not edit the public `.env.example` for this drill.

Prometheus's `up` and the explicit `outlands_demo_observed_at_seconds` are separate signals. Depending on scrape timing and query range, old samples can remain briefly visible; use a current instant view and inspect timestamps. Never turn absence into zero or call a stale sample healthy. These are synthetic modes, not a simulation of every exporter failure.

| Reader's acceptance check | Result |
| --- | --- |
| Reviewed images and Compose resolve privately | NOT RUN |
| Only loopback UI ports publish; fixture has no host port | NOT RUN |
| Grafana native login works; signed-out access is denied | NOT RUN |
| Dashboard and data source render in the selected Grafana release | NOT RUN |
| Fresh, stale, unavailable, and recovered modes appear distinctly | NOT RUN |
| State survives a controlled restart; isolated restore works | NOT RUN |

## 4. Update, reverse, and expand carefully

Keep selected image digests, settings, and state recovery material private. For an update, review upstream release notes, protect data, update one image at a time, and repeat the acceptance table. `docker compose down` stops the project without deleting named volumes; do not use `down -v` on data you intend to keep. Grafana provisioning can overwrite a matching data source or dashboard at startup; test edits in a separate project before replacing a working configuration.

If adding a real target later, create a private configuration in a separate directory and review the target's authentication, labels, freshness, retention, and data exposure. Do not add real hostnames, addresses, labels, dashboards, logs, or backup details to this public module. Metrics and query interfaces can disclose operations data; a loopback binding is only one boundary. A remote route requires its own [access review](../../access/private-entry/README.md).

`check_example.py` and its tests check source boundaries and the fictional mode generator offline. They do not start Docker, Prometheus, Grafana, or a browser. Native UI, live ingestion, identity denial, persistence, and restoration remain `NOT RUN` until the reader tests an isolated instance. Upstream docs checked 2026-10-30.
