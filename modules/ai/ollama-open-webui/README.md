# server-01 AI module: Ollama + Open WebUI

This **synthetic, CPU-default reference** runs an Ollama model server beside Open WebUI in its own Docker Compose project. An optional NVIDIA override is separate. The Ollama API is reachable only on the project network. Open WebUI is published only to host loopback. The example sets `OLLAMA_NO_CLOUD=1` for Ollama's documented local-only mode. No model is selected or pulled automatically; no remote access, account, GPU, identity provider, or existing data is imported. `server-01` is a role label, not an inventory export.

This module is optional. Read the [host reference](../../../hosts/server-01/README.md) and [module contract](../../README.md) first. The prior [AI Workbench](../../../docs/09-ai-workbench.md) page is a visual and access walkthrough; this page supplies a separate hosting example.

## Inputs and boundaries

| Input | Purpose | Public example |
| --- | --- | --- |
| `OLLAMA_IMAGE` | Reviewed Ollama image for your CPU/architecture | Blank; select a digest locally |
| `OPEN_WEBUI_IMAGE` | Reviewed Open WebUI image | Blank; select a digest locally |
| `WEBUI_SECRET_KEY` | Stable WebUI signing/encryption key | Blank; generate locally and preserve |
| `WEBUI_PORT` | Local browser port | `3001`, bound to `127.0.0.1` |

The named `ollama_models` and `open_webui_data` volumes hold models and WebUI accounts/chats respectively. Docker may store environment variables in container metadata. Keep `.env`, Compose output, logs, volume backups, and model inventories private. Do not commit a filled `.env` or share `docker compose config` output. No Docker socket is mounted.

`OLLAMA_NO_CLOUD=1` disables Ollama cloud features; it does not prevent a deliberately requested model pull from contacting a registry. Review Open WebUI's own connections and features separately. See the [Ollama local-only setting](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).

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

The first command checks the public source contract without contacting Docker. The Compose config check resolves inputs but does not start a service. Inspect the resolved configuration privately and confirm Ollama has `OLLAMA_NO_CLOUD=1`. `up -d` may download images and create containers/volumes. Use it only on the new installation you intend to create. Inspect `ps` to confirm WebUI is published solely on `127.0.0.1` and Ollama has no host port; stop if either observation differs.

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
| A reviewed model responds to a fictional prompt in Ollama and WebUI | NOT RUN |
| Optional NVIDIA profile resolves and the intended processor is observed | NOT RUN |
| Data persists through a controlled restart | NOT RUN |
| Backup restores into a separate test installation | NOT RUN |
| Any proposed remote route denies unassigned users | NOT RUN |

## 5. Select a model and plan resources privately

The public example has **no model name**. In private operator records, choose a model reference only after reviewing its upstream license, source, permitted use, size, and architecture support. Record the chosen image digests and model reference privately so an update can be compared with the previous state. Pulling a model contacts its registry and consumes disk; it is a deliberate operator action, never part of `compose up` in this example. A model's own terms are separate from this repository's license.

Plan capacity before pulling. Compare the model's published download size with free disk in the `ollama_models` volume. Leave headroom for another model during updates and for WebUI's separate data volume. Estimate RAM or VRAM for the model plus context and concurrent requests; the file size alone is not a memory budget. Ollama's [FAQ](https://docs.ollama.com/faq#how-does-ollama-handle-concurrent-requests) explains that longer context and parallel requests increase memory use. Start with one modest, licensed model and a single fictional request, observe actual use privately, then change one setting at a time. Avoid publishing host capacity, device IDs, loaded-model lists, prompts, or performance logs.

Use this short plan in **private operator notes** before pulling. Leave fields unresolved until the chosen model's source and the test host have been inspected; do not copy a filled plan into this repository.

| Private field | Decision or observation |
| --- | --- |
| Reviewed model reference and license | Record source, permitted use, and exact reference |
| Free model-volume space | Compare with download size plus update headroom |
| Available RAM and optional VRAM | Compare with model, context, and parallel-request needs |
| Initial context and parallel requests | Choose conservative values, then measure one change at a time |
| Success and stop criteria | Fictional response, WebUI visibility, and resource limit |

From the module directory on the isolated instance, ask for a reviewed model reference in the terminal so the value is not typed into a saved command. Keep this shell session private:

```sh
printf 'Reviewed model reference: '
IFS= read -r MODEL_REF
if [ -n "$MODEL_REF" ]; then
  docker compose --env-file .env -f compose.yaml exec -T ollama ollama pull "$MODEL_REF"
  docker compose --env-file .env -f compose.yaml exec -T ollama ollama ls
else
  printf 'No model selected\n' >&2
fi
```

The [Ollama CLI reference](https://docs.ollama.com/cli) documents `pull`, `ls`, `ps`, `stop`, and `rm`. `ls` shows installed models, while `ps` shows models currently loaded in memory. Do not equate an installed model with a successful inference or a working WebUI connection. To retire a model, first check whether an application still uses it, preserve required state, stop it if loaded, and remove only that exact reviewed reference. Model removal is separate from deleting the persistent volume; this guide does not run either action automatically.

## 6. Optional NVIDIA profile on a separate test host

The CPU `compose.yaml` remains the default. The [NVIDIA override](compose.nvidia.yaml) requests **one** GPU for Ollama only; it adds no host port, GPU access to WebUI, privileged mode, or Docker socket. It is an example for a reader-controlled staging host with a compatible NVIDIA driver and container toolkit. Check the current [Ollama Docker GPU guide](https://docs.ollama.com/docker) and [Docker Compose GPU reservation guide](https://docs.docker.com/compose/how-tos/gpu-support/) for the selected releases. Toolkit setup may change the Docker daemon and require a restart, so plan and validate it separately before trying this profile. This repository does not install a driver, configure the toolkit, or restart Docker.

On that test host, with the same private `.env` preparation as the CPU path, resolve both files before starting the new project:

```sh
docker compose --env-file .env -f compose.yaml -f compose.nvidia.yaml config --quiet
docker compose --env-file .env -f compose.yaml -f compose.nvidia.yaml up -d
docker compose --env-file .env -f compose.yaml -f compose.nvidia.yaml ps
```

Inspect the resolved configuration privately and confirm the reservation applies only to Ollama, WebUI remains on loopback, and Ollama still has no host port. Run the fictional inference below, then inspect `ollama ps` for the processor reported by your selected Ollama release. A successful `config` only proves the Compose model resolves; it does not prove a driver, GPU allocation, acceleration, or improved performance. If GPU use is absent or errors occur, preserve the observed failure and investigate hardware/toolkit compatibility before changing the project. AMD, Vulkan, Jetson, and multi-GPU layouts need separate hardware-specific review and are outside this override.

## 7. Prove a fictional inference and WebUI connection

The [fictional inference worksheet](inference.example.json) has a blank model reference and all results `NOT_RUN`. After the model pull completes, use the same private `MODEL_REF` shell variable to run its harmless prompt:

```sh
docker compose --env-file .env -f compose.yaml exec -T ollama ollama run "$MODEL_REF" 'Describe a fictional red paper kite in one sentence.'
docker compose --env-file .env -f compose.yaml exec -T ollama ollama ps
```

For a repeatable local check after the deliberate pull, run `python3 -I -B smoke_inference.py` in a private terminal. Add `--gpu` only for the optional NVIDIA project. The script asks for the model reference interactively, requires a private `.env`, checks that the exact model appears in this project's local inventory, and then sends only the fixed fictional prompt. It reports a nonempty-response status without printing the model name or generated text. It has no explicit pull action; if the model is removed between the inventory check and `ollama run`, stop and review any unexpected download. The script does not start containers or establish GPU use, response accuracy, WebUI connection, or access policy.

If this is the optional GPU project, include `-f compose.nvidia.yaml` in each manual Compose command above. A response should be nonempty and about the fictional prompt; **do not require exact words** from a nondeterministic model. The CLI result tests Ollama directly inside its container, not WebUI connectivity. In WebUI's native Admin/Connections view, confirm the effective Ollama endpoint is the internal `http://ollama:11434`, the reviewed model appears, and the same fictional prompt receives a response. Repeat signed-out access denial and new-registration denial after bootstrap. If a model is absent, follow the [Open WebUI connection guide](https://docs.openwebui.com/troubleshooting/connection-error/) and inspect the effective connection privately; do not publish Ollama on a host port as a shortcut. Do not use personal documents, private prompts, or live service data for a public acceptance record.

Record each observation privately with a time, image and model versions, expected and actual result, and minimal evidence reference. The worksheet is a teaching fixture, not a form to fill with real values and commit. An unavailable or failed check stays that way until retested; an offline source check cannot establish inference or authorization.

## 8. Back up, update, and roll back

Record the selected image digests and Compose input set privately. Back up **both named volumes** with a method appropriate to the host; include the stable secret key in protected recovery material. Quiesce writes or use an application-consistent backup method. Test restoration in a separate project before calling it recoverable. Do not publish archives, chats, model inventories, account databases, or restore logs.

The [disposable staging recovery method](../../../staging/server-01/README.md) demonstrates a two-volume, separate-project restore using only fictional account data and a marker in an otherwise model-free Ollama volume. It is a hosted test of that fixture, not a reader's backup result. Copy the **method**, then privately verify your own data, key handling, access denial, retention, and restore. The public example names no backup provider or destination.

After that recovery step, the hosted staging job deliberately pulls one [reviewed small instruction model](https://ollama.com/library/smollm2:135m) into the restored disposable Ollama project and checks a bounded fictional response from inside the WebUI container. Its model tag, license, size limit, resolved digest, and evidence boundary are documented in the [staging guide](../../../staging/server-01/README.md). This CI fixture is separate from the blank model choice and `NOT RUN` acceptance table for a reader's own installation.

For an update, read both upstream release notes, back up, change one reviewed image digest at a time, run `config --quiet`, recreate that service, and repeat the acceptance table. If behavior changes, return to the previous digest while keeping the volumes and key intact; database migrations can make image rollback incompatible, so use a tested restore plan rather than assuming an old image can read newer state. `docker compose down` stops the module without removing its volumes; **do not use `down -v`** on data you intend to keep.

Remote access is a separate module decision. A catalog link does not secure WebUI. Keep the native login and check both network reachability and app authorization before adding any private route. This example never enables public exposure.

## Source validation scope

`check_example.py` enforces the public example's loopback, Ollama cloud switch, volume, no-socket, blank-secret, optional GPU override, and fictional inference boundaries offline. The repository CI runs it and the offline `smoke_inference.py` contract tests. Those source checks do not verify Docker behavior, GPU access, model inference, or Open WebUI's native settings; the separate disposable hosted run reports its own result. The reader table above stays `NOT RUN` until an operator tests their own installation. Upstream docs checked 2026-10-30.
