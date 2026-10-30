# Build path: earn each next layer

Start in a disposable local workspace. Add one component at a time and keep the preceding baseline available. The repository's [README](../README.md) identifies the supplied examples and their validation status. Later stages below are an implementation path, not a claim that this repository installs a complete private platform.

## 1. Prepare a local baseline

Use a supported Docker Engine and Compose release for your operating system. Review image release notes and select an explicit version or digest; do not treat a moving tag as a reproducible pin. Create the local configuration directory before mounting it. Homepage's Docker guide describes its image, config mount, and optional user settings. This tutorial does not require the Docker socket. [Homepage Docker installation](https://gethomepage.dev/installation/docker/)

Use an explicit loopback publication for the catalog:

```yaml
ports:
  - "127.0.0.1:3000:3000"
```

Docker otherwise publishes unspecified host addresses broadly. Review IPv6 and direct-routing behavior for your deployment as well. Docker documents a localhost publishing issue in releases older than 28.0.0; use a supported version and verify the actual exposure instead of relying on this line alone. [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/)

For the commands below, `compose.yaml` means the local working copy you prepared from the README's example. Run them in that disposable directory, after resolving its required image pin:

```sh
docker compose -f compose.yaml config --quiet
docker compose -f compose.yaml up -d
curl --head --max-time 10 http://127.0.0.1:3000/
```

The first command validates the model; it does not prove runtime behavior. The second starts containers and may pull an image. The last request is a basic HTTP observation. Open the local catalog in a browser and check asset loading, readable text, and a harmless placeholder link. Keep widgets disabled until their endpoints and privileges have been reviewed. See [Compose commands](https://docs.docker.com/reference/cli/docker/compose/).

Record the image pin, UTC time, local page result, and any failure. Do not proceed if the baseline is broken.

## 2. Add explicit catalog authorization

Choose either the installed Homepage release's supported native sign-in option or a carefully integrated external gate. Do not put real users, secrets, redirect URLs, or policy exports in the public repository. Set the exact allowed Host values for the chosen route; never use a wildcard to silence an unexplained error. Follow the current upstream settings for your installed version. [Homepage authentication and Host validation](https://gethomepage.dev/installation/)

If using Authentik, begin from its current installation guide in a separate private deployment directory. Create the owner account and application assignment deliberately. A working Authentik sign-in page does not establish that the downstream app is protected. Proxy and forward-auth modes have different traffic paths; per-app authorization calls for single-application mode where applicable. Keep the integration staged until [Browser QA](03-access-and-qa.md) passes. [Authentik Compose installation](https://docs.goauthentik.io/install-config/install/docker-compose/), [proxy provider modes](https://docs.goauthentik.io/add-secure-apps/providers/proxy/)

## 3. Enable private HTTPS with Serve

Use the [optional private entry module](../modules/access/private-entry/README.md) for a full fictional allowed/denied matrix and a foreground-only route trial before deciding on persistence.

Install and enroll Tailscale using its official instructions, review your tailnet policy, and authorize any account or HTTPS changes yourself. First check the existing Serve configuration so this tutorial does not overwrite unrelated routes:

```sh
tailscale serve status
```

For an isolated node with no conflicting route, a foreground trial can proxy the locally protected catalog:

```sh
tailscale serve http://127.0.0.1:3000
```

Read the generated URL and confirm the output describes tailnet availability. Use the exact URL emitted by Serve privately. `https://workspace.domain.example` in this repository is only a reserved documentation placeholder; Serve does not provision that example name. Recheck allowed Host and external URL settings for the actual route. The foreground session can be stopped with Ctrl+C. Persist it only after QA, using the current CLI's documented background option. [Serve feature and prerequisites](https://tailscale.com/docs/features/tailscale-serve), [Serve CLI reference](https://tailscale.com/docs/reference/tailscale-cli/serve)

Do not enable public Funnel. Do not add router port forwarding to make this stage work.

## 4. Add apps individually

For each app, record its native login, allowed audience, data location, private route, backup method, and rollback compatibility. Test direct app URLs in a fresh browser session. Add its Homepage tile only after the access decision has been checked. Homepage service entries can group and link apps without configuring an integration widget. [Homepage service configuration](https://gethomepage.dev/configs/services/)

Grafana keeps its native login in this build path. Defer shared app sign-in until an independent integration and role review is complete. [Grafana authentication](https://grafana.com/docs/grafana/latest/setup-grafana/configure-access/configure-authentication/)

## 5. Add telemetry, then branding

Collect a small approved host metric set first. Check one host and a known time range before adding fleet-wide aggregation. Keep data sources private and apply the [read-only boundary](03-access-and-qa.md#read-only-data-boundary). Use [branding](04-branding.md) after functionality and access checks pass. Complete [operations and recovery checks](05-operations.md) before calling any deployment operational.
