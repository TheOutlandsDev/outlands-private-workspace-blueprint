# Synthetic server-01 staging result

The [hosted run #7](https://github.com/TheOutlandsDev/outlands-private-workspace-blueprint/actions/runs/41071913498) completed successfully on 2026-10-30 for commit `dad0047e925d8dd2cb53ca3411e26ec3eafebe2a` in [PR #14](https://github.com/TheOutlandsDev/outlands-private-workspace-blueprint/pull/14). The separate [public source checks](https://github.com/TheOutlandsDev/outlands-private-workspace-blueprint/actions/runs/41071913434) also passed for that commit. This receipt describes that disposable runner, not a reader's installation.

| Hosted check | Observed result |
| --- | --- |
| Six containers and published ports | PASS: Homepage, WebUI, Grafana and Prometheus used loopback; Ollama and the fictional fixture had no host port |
| AI connection and account boundary | PASS: Ollama CLI, WebUI-to-Ollama API, fictional first owner as admin, second signup denied, signed-out session denied |
| Fictional metrics and Grafana | PASS: source scrape, administrator login, datasource and three-panel dashboard provisioning, fresh → stale → unavailable → recovered states |
| Chromium UI | PASS: fictional Homepage cards and exact `.invalid` destinations, signed-out WebUI screen, Grafana login and synthetic dashboard render |

Registry digests resolved and used within that run:

| Image | Resolved digest |
| --- | --- |
| Homepage | `ghcr.io/gethomepage/homepage@sha256:19c5c09184458a41b7b5915e71463a39f36cd33540f41bdbed008791b8182d5f` |
| Ollama | `ollama/ollama@sha256:b2f0122c476bc9fe7ce679d8bb4bd555351e25e2554eefb156f61cb0a89cf429` |
| Open WebUI | `ghcr.io/open-webui/open-webui@sha256:03443b8de6b617da9d900edd09b4bf1cb0ddbfdcba6afb42c548336a0b821ded` |
| Python | `python@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb` |
| Prometheus | `prom/prometheus@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2` |
| Grafana | `grafana/grafana@sha256:488984b716c0862639f91a698adbe2862677a5a07bad42da5f03f3030883b205` |

The runner pulls upstream version tags, then uses the resolved digests for its Compose projects. Tags can change later; a later run needs its own digest and result review. Earlier runs in [PR #13](https://github.com/TheOutlandsDev/outlands-private-workspace-blueprint/pull/13) failed during startup readiness, Grafana authentication, and strict Homepage DOM assertions. Those failures remain visible and led to the corrected checks and Grafana file-provider configuration.

Model download and inference, GPU use, private network routes, physical devices, durable recovery, upgrades, and any real host remain **NOT RUN**. No operator data, backup destination, or live service was supplied to this staging job.
