# OUTLANDS module contract

Modules are optional parts of a `server-01`-style host. A module must identify its prerequisites, configurable inputs, listening addresses, persistent state, installation sequence, validation, backup, upgrade, and rollback. It must keep local secrets and operator records out of Git. An example module can be useful without being a complete production installer.

| Module | Role | Status |
| --- | --- | --- |
| [Docker host foundation](foundation/docker-host/README.md) | Linux/Docker setup guidance and isolated smoke check | Synthetic reference; offline source and Compose checks |
| [Ollama + Open WebUI](ai/ollama-open-webui/README.md) | Local model server, authenticated browser UI, and optional NVIDIA example | Synthetic CPU default and one-GPU override; inference and native UI NOT RUN |
| [Private entry](access/private-entry/README.md) | Optional staged access to a locally protected app | Fictional route and NOT RUN access review; no live policy export |
| [Synthetic observability](observability/synthetic-metrics/README.md) | Local-only Prometheus/Grafana with a fictional source | Offline source checks; native GUI and ingestion NOT RUN |
| [Homepage catalog](catalog/homepage/README.md) | Optional local entry page with fictional WebUI and monitoring links | No app integration, shared login, or route; native UI NOT RUN |

Use each module in a separate Compose project. A module may declare a dependency on a host capability such as Docker, but must not silently install another service or modify an existing deployment. Public examples use invented labels and empty secret values. Operators select images, data handling, access policy, and recovery arrangements privately. Public modules must not identify backup providers, accounts, paths, buckets, or endpoints.

The [server-01 host reference](../hosts/server-01/README.md) describes the role; its [assembly guide](../hosts/server-01/ASSEMBLY.md) provides the staged order and a fictional acceptance worksheet. More modules can follow the same contract without requiring the AI example.
