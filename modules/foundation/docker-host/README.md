# server-01 foundation: Linux and Docker

This is a **synthetic host foundation**, not a copy of an operator's machine. `server-01` names a role that readers can recreate on a supported Linux host. The module installs nothing automatically and contains no accounts, storage locations, network addresses, firewall rules, credentials, or actual host inventory. It prepares the boundary used by optional [OUTLANDS modules](../../README.md), including the separate [AI module](../../ai/ollama-open-webui/README.md).

## What this module supplies

| Part | Public contract | What the operator decides privately |
| --- | --- | --- |
| Host | Supported Linux and Docker Engine with Compose plugin | Distribution, hardware, disk layout, update window |
| Docker access | Deliberate privileged access to the daemon | Who may use the daemon and how |
| Projects | One Compose project per optional module | Local project names and settings |
| Smoke check | One disposable, network-disabled container | Reviewed image digest and runtime acceptance |
| Recovery | Document state and prove a separate restore | All private recovery arrangements |

Docker daemon access is powerful: Docker's [Linux post-installation guide](https://docs.docker.com/engine/install/linux-postinstall/) notes that the `docker` group grants root-level privileges. Do not add users to that group merely to make a tutorial command succeed. This guide does not change groups, start Docker, install packages, or modify a firewall.

## 1. Prepare your Linux host

1. Choose a Linux release supported by [Docker Engine](https://docs.docker.com/engine/install/) and your hardware. Use the official instructions for that release to install Docker Engine and the Compose plugin. Review package source, service startup behavior, and required privileges before applying any commands to an existing machine.
2. Set host update, logging, disk, and recovery policies in private operator records. Do not publish the host's package inventory, disk layout, network map, account list, daemon configuration, or recovery destination.
3. Decide how authorized operators access Docker. A user able to control the daemon can affect the host; use the [upstream post-installation guidance](https://docs.docker.com/engine/install/linux-postinstall/) and test the chosen access method in your environment. This repository does not prescribe group membership or rootless mode for all hosts.
4. Confirm the client, server, and Compose plugin respond. Keep full diagnostic output private because it can include host details:

```sh
docker version --format '{{.Server.Version}}'
docker compose version --short
```

These print version values only. They do not prove service isolation, safe firewall policy, disk capacity, or that another user's Docker access is denied.

## 2. Use separate projects

Keep each optional module in its own directory and Compose project. Review a module's image digest, required inputs, ports, networks, volumes, and data policy before running it. Do not share the Docker socket with a browser-facing service. Prefer explicit loopback bindings for local UIs; add any remote route only after its own authorization and denial checks. A catalog link is not an access control.

Compose project names help separate resources, but an operator must still check for name collisions and shared external networks. The [Docker project-name guide](https://docs.docker.com/compose/how-tos/project-name/) explains naming and precedence. The AI module publishes only its WebUI on loopback; this foundation's smoke service publishes no port and joins no network.

## 3. Run the isolated smoke example

Use a new test host or a deliberately chosen Docker context. From this module directory:

```sh
umask 077
cp .env.example .env
chmod 600 .env
docker pull hello-world:latest
docker image inspect --format '{{index .RepoDigests 0}}' hello-world:latest
```

The pull contacts a registry and downloads an image; it does not start a container. Review that this is the intended [Docker example image](https://docs.docker.com/engine/install/linux-postinstall/) and record its returned `@sha256:` digest privately. Put that exact reference in `SMOKE_IMAGE` inside `.env`. The checked-in `.env.example` is intentionally blank, and `.gitignore` excludes filled `.env` files. Do not commit the resolved digest if it reveals your private deployment choices.

```sh
python3 -I -B check_example.py
docker compose --env-file .env -f compose.yaml config --quiet
docker compose --env-file .env -f compose.yaml run --rm --no-deps smoke
```

The offline checker examines only this public fixture. `config --quiet` resolves the file but does not launch a container. `run --rm` starts one disposable container; expect the upstream image's success message and exit status 0. The Compose service has no port, volume, Docker socket, or container network, uses a read-only root filesystem, drops capabilities, and requests no new privileges. These controls constrain the smoke example; they do not establish that every future module or the host itself is secure. A failed pull, daemon error, or nonzero exit remains a failure to investigate, not a reason to change host permissions blindly.

## 4. Validate each next module

| Check | Reader's host result |
| --- | --- |
| Official Docker installation and chosen access method reviewed | NOT RUN |
| Client, daemon, and Compose plugin respond in the intended context | NOT RUN |
| Smoke Compose resolves and isolated container exits successfully | NOT RUN |
| No unintended host port, shared network, or privileged mount exists | NOT RUN |
| AI module's local UI and account boundary pass separately | NOT RUN |
| State is recoverable in a separate test environment | NOT RUN |

Do not paste full `docker info`, `docker inspect`, package listings, logs, or host paths into public issues. Record only the minimal non-sensitive outcome needed to reproduce a problem. A successful smoke run establishes a narrow container-runtime result, not a ready production host.

## 5. Update and reverse safely

Read the selected Linux and Docker release notes, record the current versions and affected modules privately, then update in a planned maintenance window. Validate the daemon, Compose, smoke example, and each affected module independently. Keep application state and any recovery details private. If an update fails, follow the platform's supported recovery procedure and the affected module's tested restore plan; do not delete volumes or reset the daemon to make a check pass.

For this smoke example, `run --rm` removes its one-off container after exit. No application data volume or live host setting is created by this repository. The [offline source checker](check_example.py) and negative tests verify the published fixture only. Runtime, access, update, and recovery rows remain `NOT RUN` until tested by the reader. Docker documentation checked 2026-10-30.
