# OUTLANDS module contract

Modules are optional parts of a `server-01`-style host. A module must identify its prerequisites, configurable inputs, listening addresses, persistent state, installation sequence, validation, backup, upgrade, and rollback. It must keep local secrets and operator records out of Git. An example module can be useful without being a complete production installer.

| Module | Role | Status |
| --- | --- | --- |
| [Ollama + Open WebUI](ai/ollama-open-webui/README.md) | Local model server and authenticated browser UI | Synthetic CPU reference; offline source and Compose checks |

Use each module in a separate Compose project. A module may declare a dependency on a host capability such as Docker, but must not silently install another service or modify an existing deployment. Public examples use invented labels and empty secret values. Operators select images, data handling, access policy, and recovery arrangements privately. Public modules must not identify backup providers, accounts, paths, buckets, or endpoints.

The [server-01 host reference](../hosts/server-01/README.md) describes the role and assembly order. More modules can follow the same contract without requiring the AI example.
