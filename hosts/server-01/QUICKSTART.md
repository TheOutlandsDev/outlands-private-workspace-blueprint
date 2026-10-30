# server-01 reader quick-start

Use this path to build a **reader-owned, fictional** OUTLANDS test host one module at a time. It starts with local Ollama and Open WebUI; fictional metrics and the Homepage catalog are optional. `server-01` names a role, not an inventory entry. This guide does not install Docker, choose hardware or models, configure a remote route, or select a backup destination.

Work from a downloaded copy of this repository on a Linux test host. Install a supported Docker Engine and Compose plugin using [Docker's official instructions](https://docs.docker.com/engine/install/) and review [daemon access](https://docs.docker.com/engine/security/#docker-daemon-attack-surface) before granting an account Docker control. Python 3.9+ is used by the local helpers. Do not run the examples against a production Docker context.

## 1. Check the public source and the selected local Docker context

From the repository root:

```sh
python3 -I -B hosts/server-01/check_assembly.py
python3 -I -B hosts/server-01/preflight.py
```

The assembly check reads public files only. The preflight reads the selected Docker context, checks for the Compose plugin, and asks the **local Unix-socket daemon** for its version. It starts no services, prints only bounded PASS/REVIEW flags, and refuses `DOCKER_HOST`, `DOCKER_CONTEXT`, SSH, or TCP contexts. Stop if either command reports REVIEW. Resolve the context privately; never paste `docker info`, Compose output, or a filled environment file into a public issue.

### Optional one-shot host snapshot

The [host-health module](../../modules/observability/host-health/README.md) is independent of Docker and the fictional Prometheus/Grafana dashboard. Its default published examples use invented counters. After reviewing its source, a reader may choose a one-shot `--live` check or a bounded foreground trend run on their own Linux host. The latter writes readings only to a new private directory and renders a static local dashboard; it does not install, schedule, or export a service. Follow that module's separate opt-in instructions. Neither result completes a Docker or application acceptance gate.

```sh
python3 -I -B modules/observability/host-health/host_health.py --fictional
```

## 2. Make a private local working copy

Choose a new absolute directory **outside the repository**. The example below uses a reader-owned home directory; choose your own private location and keep it out of Git.

```sh
python3 -I -B hosts/server-01/prepare_local.py --destination "$HOME/outlands-server-01-example"
```

The helper refuses an existing destination, validates the fictional [assembly worksheet](assembly.example.json), and copies only named public runtime files into `ai/`, `metrics/`, and `catalog/`. It creates mode-0600 blank `.env` files, an empty private `metrics/.secrets/` directory, and a mode-0600 `acceptance.json` worksheet with every gate at `NOT_RUN`. It does not fill credentials, pull images, contact Docker, or start services. A failed copy may leave a partial directory for private inspection; it never deletes or overwrites it automatically.

## 3. Start the AI project locally

Read the [AI module guide](../../modules/ai/ollama-open-webui/README.md). In the private `ai/.env`, fill `OLLAMA_IMAGE` and `OPEN_WEBUI_IMAGE` with reviewed immutable image digests for your architecture. Generate a fresh `WEBUI_SECRET_KEY` locally and keep that key with the two named volumes in your **private** recovery plan. Select an unused `WEBUI_PORT`; the Compose file binds WebUI only to `127.0.0.1`, and Ollama has no host port. Keep CPU mode first; the NVIDIA overlay has a separate qualification path.

After reviewing the filled private file, run from the private AI directory:

```sh
cd "$HOME/outlands-server-01-example/ai"
docker compose --env-file .env -f compose.yaml config --quiet
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
```

`up -d` can pull the chosen images and creates the AI network and persistent volumes. Check the actual port bindings before opening the local WebUI. On a **new** WebUI volume, create the first owner account in the local browser, disable signup in the effective Admin UI, sign out, and verify a second registration and signed-out content access are denied. Keep any account names, screenshots, and logs private. If you later choose and review a model, the copied `smoke_inference.py` checks an **already installed** model with a fixed fictional prompt from a private terminal; it does not download one. Record inference as `NOT_RUN` until you actually perform that check.

## 4. Add fictional metrics only after its own preparation

The private `metrics/` copy contains a fictional source and dashboard; it has no host, AI, or Docker telemetry. Follow the [metrics module guide](../../modules/observability/synthetic-metrics/README.md) to select three reviewed digests, create its local Grafana password file, and confirm the selected image can read that file. Keep the password and selected image details private. Then, from the private metrics directory:

```sh
cd "$HOME/outlands-server-01-example/metrics"
docker compose --env-file .env -f compose.yaml config --quiet
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
```

Confirm Grafana and Prometheus publish only on the chosen loopback ports; the fixture has no host port. In the native Grafana UI, verify login denial and the fictional fresh, stale, unavailable, and recovered states. Do not turn a successful scrape into a claim that host or AI health is monitored.

## 5. Add the catalog without granting access

Follow the [Homepage catalog module guide](../../modules/catalog/homepage/README.md). Fill the private `catalog/.env` with a reviewed image digest, intended local IDs, and an unused loopback port. If the port changes, update both exact allowed-host entries. Ensure the selected IDs can write the private `config/` directory. Then:

```sh
cd "$HOME/outlands-server-01-example/catalog"
docker compose --env-file .env -f compose.yaml config --quiet
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
```

The two public cards intentionally use `.invalid` destinations. Check the native Homepage page first. Replace a card only in your private copy, after that destination's own login and access checks pass. A catalog link does not authorize a user. The optional [private entry trial](../../modules/access/private-entry/README.md) is a separate step with its own allowed and denied tests; do not infer it from local success.

## 6. Record what actually passed

Use the private `acceptance.json` made in step 2 and the fuller [assembly guide](ASSEMBLY.md). For each module, record the observation time, selected software snapshot, expected result, actual result, and a private evidence reference. Leave an unrun or failed gate as such. In particular, model inference, GPU use, real private routes, state retention, and restoration on **your** host are not established by the repository's [disposable hosted staging](../../staging/server-01/README.md).

Keep all filled `.env` files, credentials, routes, model inventories, prompts, private dashboard exports, and every backup provider or destination outside the public repository. Do not upload the private working copy. Stop one project at a time; avoid `docker compose down -v` when you intend to preserve its volumes. Before any update, privately test a consistent archive and an isolated restore for the affected project.
