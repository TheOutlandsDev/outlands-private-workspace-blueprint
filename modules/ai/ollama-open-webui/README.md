# server-01 AI module: Ollama + Open WebUI

This **synthetic, CPU-oriented reference** runs an Ollama model server beside Open WebUI in its own Docker Compose project. The Ollama API is reachable only on the project network. Open WebUI is published only to host loopback. No model is selected or pulled automatically; no remote access, account, GPU, identity provider, or existing data is imported. `server-01` is a role label, not an inventory export.

This module is optional. Read the [host reference](../../../hosts/server-01/README.md) and [module contract](../../README.md) first. The prior [AI Workbench](../../../docs/09-ai-workbench.md) page is a visual and access walkthrough; this page supplies a separate hosting example.

## Inputs and boundaries

| Input | Purpose | Public example |
| --- | --- | --- |
| `OLLAMA_IMAGE` | Reviewed Ollama image for your CPU/architecture | Blank; select a digest locally |
| `OPEN_WEBUI_IMAGE` | Reviewed Open WebUI image | Blank; select a digest locally |
| `WEBUI_SECRET_KEY` | Stable WebUI signing/encryption key | Blank; generate locally and preserve |
| `WEBUI_PORT` | Local browser port | `3001`, bound to `127.0.0.1` |

The named `ollama_models` and `open_webui_data` volumes hold models and WebUI accounts/chats respectively. Docker may store environment variables in container metadata. Keep `.env`, Compose output, logs, volume backups, and model inventories private. Do not commit a filled `.env` or share `docker compose config` output. No Docker socket is mounted.

## 1. Prepare a new, isolated installation

Use a supported Linux host with Docker Engine and its Compose plugin. Check the current [Ollama Docker guide](https://docs.ollama.com/docker), [Open WebUI quick start](https://docs.openwebui.com/getting-started/quick-start/), and [environment reference](https://docs.openwebui.com/reference/env-configuration/) for your chosen releases. Review their licenses separately; this repository's MIT license covers only original OUTLANDS material. Select immutable image digests from the official images for your architecture. CPU is the default example; a GPU requires a separate, hardware-specific review and container runtime setup.

From this module directory, on a **new test host or isolated staging project**:

```sh
umask 077
cp .env.example .env
chmod 600 .env
openssl rand -hex 32
```

Edit `.env` privately: set both image references to reviewed `@sha256:` digests and paste the generated key as `WEBUI_SECRET_KEY`. Keep the key stable across restarts and backups. Do not put it in a command argument, ticket, screenshot, or this repository. Choose a free `WEBUI_PORT` if 3001 is occupied. The `.gitignore` excludes `.env` files.

## 2. Resolve, inspect, and start

```sh
python3 -I -B check_example.py
docker compose --env-file .env -f compose.yaml config --quiet
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
```

The first command checks the public source contract without contacting Docker. The Compose config check resolves inputs but does not start a service. `up -d` may download images and create containers/volumes. Use it only on the new installation you intend to create. Inspect `ps` to confirm WebUI is published solely on `127.0.0.1` and Ollama has no host port; stop if either observation differs.

## 3. Bootstrap the owner locally

Open `http://127.0.0.1:3001/` on the host, using your selected port. The first account created on a fresh Open WebUI data volume becomes its administrator under the upstream bootstrap flow. Create that account before providing any remote route. **Immediately disable sign-up in Open WebUI Admin settings**, then sign out and confirm a second account cannot register. The Compose `ENABLE_SIGNUP` value is intentionally for this initial local bootstrap. Open WebUI persists some configuration in its database, so changing the environment variable later may not change the effective setting; inspect the Admin UI and test the result. Never delete the data volume to force a setting change. Keep the UI on loopback until access, signup, authentication, and backup checks pass.

## 4. Validate the new instance

```sh
docker compose --env-file .env -f compose.yaml exec -T ollama ollama list
curl --fail --silent --show-error --max-time 10 -o /dev/null http://127.0.0.1:3001/
```

An empty model list is expected before you deliberately select and pull a model. These checks prove only that the commands reached the new services; they do not prove inference, owner-only access, persistence, or restoration. For a permitted model, review its separate license, size, and resource needs, then pull it through the upstream Ollama workflow and run a harmless synthetic prompt. Do not use private prompts or production documents for acceptance tests. Inspect WebUI's effective Ollama connection and verify a model appears and responds. If the UI connection fails, check `OLLAMA_BASE_URL` in the running container and use the [upstream connection guide](https://docs.openwebui.com/troubleshooting/connection-error/).

| Acceptance check | New installation result |
| --- | --- |
| Compose resolves with chosen image digests and private key | NOT RUN |
| Only WebUI loopback port is published; Ollama has no host port | NOT RUN |
| First owner can sign in; signed-out registration is denied after bootstrap | NOT RUN |
| A reviewed model responds to a synthetic prompt | NOT RUN |
| Data persists through a controlled restart | NOT RUN |
| Backup restores into a separate test installation | NOT RUN |
| Any proposed remote route denies unassigned users | NOT RUN |

## 5. Back up, update, and roll back

Record the selected image digests and Compose input set privately. Back up **both named volumes** with a method appropriate to the host; include the stable secret key in protected recovery material. Quiesce writes or use an application-consistent backup method. Test restoration in a separate project before calling it recoverable. Do not publish archives, chats, model inventories, account databases, or restore logs.

For an update, read both upstream release notes, back up, change one reviewed image digest at a time, run `config --quiet`, recreate that service, and repeat the acceptance table. If behavior changes, return to the previous digest while keeping the volumes and key intact; database migrations can make image rollback incompatible, so use a tested restore plan rather than assuming an old image can read newer state. `docker compose down` stops the module without removing its volumes; **do not use `down -v`** on data you intend to keep.

Remote access is a separate module decision. A catalog link does not secure WebUI. Keep the native login and check both network reachability and app authorization before adding any private route. This example never enables public exposure.

## Source validation scope

`check_example.py` enforces the public example's loopback, volume, no-socket, and blank-secret boundaries offline. The repository CI runs it and its negative tests. It does not verify Docker behavior or Open WebUI's native settings; the table above stays `NOT RUN` until an operator tests their own installation. Upstream docs checked 2026-10-30.
