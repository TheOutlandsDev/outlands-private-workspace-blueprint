# server-01: OUTLANDS host reference

`server-01` is the **example host role** for a modular OUTLANDS installation. It is a synthetic name in this public guide, not a host inventory or an export of an operator's machine. Bring your own host name, storage plan, accounts, and network policy in private local configuration.

## Assemble a host

| Layer | Interface | Current example |
| --- | --- | --- |
| Host | Linux host with a supported Docker Engine and Compose plugin | [Foundation module](../../modules/foundation/docker-host/README.md) |
| Storage | Persistent state with a privately chosen recovery plan | Named volumes in the AI module |
| Network | Local binding first; remote route only after separate access review | [Private entry module](../../modules/access/private-entry/README.md); WebUI stays on loopback |
| AI | Model server, browser application, and optional GPU profile | [Ollama + Open WebUI](../../modules/ai/ollama-open-webui/README.md) |
| Catalog | Optional entry point after the app access check | [Homepage example](../../examples/homepage/README.md) |
| Monitoring | Optional, with its own authorization and retention plan | [Synthetic observability module](../../modules/observability/synthetic-metrics/README.md) |

Follow the [assembly guide](ASSEMBLY.md) for the staged order, private decisions, and cross-module acceptance worksheet. Modules do not need a shared login or a single all-services Compose file. Start with the [foundation module](../../modules/foundation/docker-host/README.md), then install one optional service into its own project and verify its boundary before linking it from the catalog. The [module contract](../../modules/README.md) explains which parts each module must document.

## Host preparation checklist

1. Choose a supported Linux release and follow its official installation and update instructions. Keep disk layout, recovery media, and every backup location or provider in private operator records. This public role does not describe an actual host.
2. Install Docker Engine and Compose from the [official Docker instructions](https://docs.docker.com/engine/install/). Review Docker's daemon and group privileges; membership in the `docker` group grants powerful host control.
3. Check `docker version` and `docker compose version` before using a module. Use an ordinary operator account with deliberate Docker access; do not paste credentials into a Compose file or shell history.
4. Pick one module, copy its example settings to a Git-ignored local file, and resolve its configuration before starting it. Check its intended listening addresses and persistent volumes.
5. Take a tested backup before upgrades. Keep host inventory, account lists, model names, network addresses, logs, and recovery keys outside this public repository.

The first supported example is CPU-oriented. GPU use, model choice, identity integration, remote access, and production hardening remain operator-selected extensions. The current repository has not booted this stack on a real server or qualified a particular GPU.
