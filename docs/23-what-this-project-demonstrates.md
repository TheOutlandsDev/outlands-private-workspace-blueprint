# What this workspace demonstrates

The blueprint teaches how to build and explain a private application workspace. Its public examples are original and fictional; they do not disclose a real deployment or claim that every upstream application supports the same theme or access method.

| Practice | Inspectable example | Test or decision boundary |
| --- | --- | --- |
| Observability | [Synthetic Prometheus/Grafana module](../modules/observability/synthetic-metrics/README.md) | Fictional state generator and source checks do not prove native dashboard or live ingestion. |
| Private entry | [Staged route guide and fictional access review](../modules/access/private-entry/README.md) | Offline fixture checks do not prove network or app authorization. |
| Host foundation | [Linux/Docker guide and isolated smoke fixture](../modules/foundation/docker-host/README.md) | Source and Compose resolution are separate from an installed daemon or a successful container run. |
| Modular host | [server-01 role](../hosts/server-01/README.md), [module contract](../modules/README.md), and [Ollama + Open WebUI example](../modules/ai/ollama-open-webui/README.md) | Source and Compose checks do not prove a booted host, model inference, or an access policy. |
| System design | [Architecture](01-architecture.md), [build path](02-build-path.md), and [Homepage example](../examples/homepage/README.md) | Compose resolution is separate from a running service. |
| Access design | [Owner access matrix](03-access-and-qa.md) | Allowed access and denial need separate observations. |
| Interface work | [App walkthroughs](07-app-walkthroughs.md) and original fictional demos | A static mockup is separate from a native application or physical phone. |
| Operations | [Backup and recovery method](05-operations.md) | A created snapshot is separate from a tested restore. |
| Evidence | [Delivery method](21-evidence-driven-delivery.md) and [offline ledger example](../examples/evidence-ledger/README.md) | A structurally valid record does not prove its observation. |
| Public release | [Publication review](22-publication-review.md), [fictional worked example](24-fictional-release-walkthrough.md), and [source checker](../scripts/check_public_source.py) | No scan or hash match guarantees privacy or rights clearance. |

Standalone public utilities live in [OUTLANDS Public Tools](https://github.com/TheOutlandsDev/outlands-public-tools). Relevant examples include the [Public Release Audit](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/public-release-audit), [Hash Journal](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/hash-journal), and [Server Maintenance Planner](https://github.com/TheOutlandsDev/outlands-public-tools/tree/main/tools/server-maintenance). Each has its own README and limits. Linking to a tool does not run it against a server or qualify it for a new environment.

The most useful contribution to this project is a small, reproducible improvement: a fictional fixture, a clearly bounded check, a readable result, and an explanation of what remains untested. See [Contributing](../CONTRIBUTING.md).
