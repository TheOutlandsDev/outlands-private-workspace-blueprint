# server-01 catalog: fictional Homepage links

This optional module runs **only Homepage** as a local entry page for a `server-01`-style OUTLANDS host. It contains two fictional cards: Open WebUI and an optional Grafana destination. Their `.invalid` URLs are deliberately unusable. The catalog does not deploy either application, scrape their data, replace their native login, or provide single sign-on. It does not mount the Docker socket or enable API widgets. `server-01` is a synthetic role, not a live inventory entry.

The [host assembly guide](../../../hosts/server-01/ASSEMBLY.md) and [module contract](../../README.md) explain the broader sequence. The original [local Homepage starter](../../../examples/homepage/README.md) remains a separate visual example; this module gives the host role its own configurable catalog project. Homepage's current [Docker installation](https://gethomepage.dev/installation/docker/) and [service-card configuration](https://gethomepage.dev/configs/services/) are the upstream references for the chosen image release.

## Inputs and boundaries

| Input | Public example | Private operator choice |
| --- | --- | --- |
| `HOMEPAGE_IMAGE` | Blank | Reviewed immutable image digest for the host architecture |
| `CATALOG_PORT` | `3003`, bound to `127.0.0.1` | Unused local port |
| `HOMEPAGE_ALLOWED_HOSTS` | `localhost:3003,127.0.0.1:3003` | Exact hostnames and ports for a separately reviewed route |
| `PUID`, `PGID` | Blank | Intended local user and group IDs with access to `config/` |
| `config/services.yaml` | Two `.invalid` card destinations | Private destinations only after each app's access review |

The `config/` bind mount holds settings and may gain application-generated files when Homepage runs. It is not a secret store. Still keep the working configuration, URLs, logs, and any screenshots containing private labels out of this public repository. The example has no named data volume and no model or metrics state. A catalog card is a link, not proof that its destination is reachable or authorized.

## 1. Prepare a private test copy

First check the **published fictional fixture** from the repository root:

```sh
python3 -I -B modules/catalog/homepage/check_example.py
python3 -I -B -m unittest discover -s modules/catalog/homepage -p 'test_*.py'
```

Then copy the entire `modules/catalog/homepage/` directory into a private, isolated test location **outside the Git checkout**. Work in that copy. Do not add real destinations to the checked-in example. Review the selected [Homepage package](https://github.com/gethomepage/homepage/pkgs/container/homepage), its release notes, and license; choose an immutable `@sha256:` image reference for your architecture. The repository does not choose an image version.

From the private copy:

```sh
umask 077
cp .env.example .env
chmod 600 .env
id -u
id -g
```

Fill `HOMEPAGE_IMAGE`, `PUID`, and `PGID` in `.env` with privately reviewed values. Check that the chosen IDs can write `config/` before starting the container; do not change unrelated filesystem ownership just to make the example run. If you change `CATALOG_PORT`, update **both** loopback entries in `HOMEPAGE_ALLOWED_HOSTS` to the same port. Add a private route hostname only after its own access decision; never use `*` or a broad allowed-host list. A filled `.env` is Git-ignored and should remain in the private copy.

## 2. Resolve and start only the catalog

```sh
docker compose --env-file .env -f compose.yaml config --quiet
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
```

`config --quiet` resolves configuration without starting anything. `up -d` may pull the chosen image and creates only this module's container and network. Review `ps`: the sole published port should be the chosen `127.0.0.1` catalog port. There is no Docker socket mount, API widget, or connection to the AI or observability Compose networks. Stop if the actual bindings differ. Keep Compose output private because it can include operator choices.

Open `http://127.0.0.1:3003/` on the test host, or your selected port. Confirm the **FICTIONAL CATALOG** title, original OUTLANDS wall artwork, two cards, and their placeholder descriptions in the native Homepage UI. The `.invalid` links should not lead to a live app. The two SVGs are copies of this repository's original [Homepage starter artwork](../../../examples/homepage/README.md); the mount is limited to `/app/public/outlands`. Check the chosen image release's [settings documentation](https://gethomepage.dev/configs/settings/) if the native page differs. Source checks and Compose resolution do not prove that this UI renders correctly; the reader's acceptance table below starts at `NOT RUN`.

## 3. Replace links only after destination checks

Complete the [Ollama/Open WebUI module](../../ai/ollama-open-webui/README.md) first: the owner account works, sign-up is disabled, signed-out users see no protected content, and any private route has passed both network and app denial checks. In the **private copy**, replace only the WebUI card's `href` with that reviewed destination. A URL such as `127.0.0.1` in a card points to the **viewer's** device, so use a destination that works for the intended viewer and has its own access boundary. Do not place a Docker-internal name such as `ollama` in a browser link.

The Grafana card is optional. Leave its `.invalid` placeholder until the monitoring module's native login and any proposed private route are reviewed separately. Do not copy the WebUI route or automatically expose Prometheus or Grafana. Remove the card in your private copy if monitoring should not appear. Avoid service widgets, API keys, site monitors, and ping checks unless you separately review what they send and reveal. The public catalog contains no such integration.

If you give other devices access to **Homepage itself**, apply a narrow private network policy or a separately tested owner gate. This example has no catalog login. Test an intended owner and an unassigned identity/device in fresh browser sessions; prove the unassigned case cannot read the catalog or a direct app URL. A catalog route and each destination app's native login are separate boundaries. Never use Funnel or public router forwarding as a shortcut for this private example. Keep actual hostnames, policy, cookies, and screenshots private.

## 4. Validate and reverse

| Reader's acceptance check | Result |
| --- | --- |
| Chosen image digest and local IDs reviewed; Compose resolves privately | NOT RUN |
| Only the catalog loopback port publishes; no Docker socket or API widget | NOT RUN |
| Native Homepage title and two fictional cards render | NOT RUN |
| WebUI destination opens only after its own app login and access checks | NOT RUN |
| Optional Grafana destination has its own login and route review | NOT RUN |
| Unassigned identity/device cannot read a remotely routed catalog | NOT RUN |
| Stopping the project preserves private configuration and unrelated services | NOT RUN |

For a configuration change, keep a private copy of the previous files, update only this project, and repeat the affected UI and denial checks. `docker compose down` stops this project's container and network; it does not remove the bind-mounted `config/` directory. Review the exact project name before running it on a shared host. A failed or unrun check remains incomplete; do not call a link secure merely because it appears on the page.

`check_example.py` and its negative tests inspect the **public fixture** offline. They reject a real destination, wildcard port, Docker socket, API widget, or filled public inputs. They are deliberately not a validator for an operator's private configuration and do not run Docker or a browser. Native rendering, routing, authorization, update, and recovery remain `NOT RUN` until a reader tests an isolated instance. Upstream Homepage docs checked 2026-10-30.
