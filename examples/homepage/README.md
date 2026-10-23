# Local Homepage starter

This example starts only Homepage. It does not deploy an identity provider,
Docker manager, collector or other app. All catalog destinations are reserved
`.invalid` placeholders and must be replaced with your own reviewed private URLs.
It has not been boot-tested in this repository's release checks.

## Prepare a working copy

Use a disposable local directory or this example directory. Docker Engine with
Compose and an ordinary local user are prerequisites. Follow the official
[Homepage Docker guide](https://gethomepage.dev/installation/docker/) for your
image version. The example uses the documented PUID/PGID startup behavior and
retains upstream entrypoint/default capabilities; it is not a complete production
hardening baseline.

```sh
cd examples/homepage
cp .env.example .env
id -u
id -g
```

Edit your private `.env`: set PUID/PGID to those numeric IDs and set HOMEPAGE_IMAGE
to a reviewed immutable image reference obtained from the official
[Homepage package](https://github.com/gethomepage/homepage/pkgs/container/homepage).
For example, the reference format is `ghcr.io/gethomepage/homepage@sha256:<digest>`;
replace the angle-bracket placeholder with the real reviewed digest. No digest
in this guide is claimed to identify a current or verified image.

Ensure `config/` is writable by that UID/GID and assets are readable. Check your
own directory ownership before making any permission change. Existing unrelated
files should not be modified. Homepage may create local config/log files.

```sh
# Resolve local configuration only; no app is started by this command.
docker compose --env-file .env -f compose.yaml config --quiet

# This starts a new local app and may download your selected image.
# Run only after reviewing the configuration and local port availability.
docker compose --env-file .env -f compose.yaml up -d
```

Open `http://127.0.0.1:3000/` on the same machine. Confirm the title, red artwork,
cards and text. Placeholder destination links are intentionally not working apps.
No Docker socket is mounted and there are no API-backed service widgets.

## Add private HTTPS separately

Once the local view works, read [the build path](../../docs/02-build-path.md) and
[access QA](../../docs/03-access-and-qa.md). Add the exact private hostname, including
port if required, to HOMEPAGE_ALLOWED_HOSTS. Do not use a wildcard. Recreate only
your new Homepage example if that environment value changes.

Tailscale Serve provides private routing; it does not by itself implement an
owner role. Before adding administrative apps, design explicit tailnet policy
and the destination's native authorization or a reviewed owner gate. Do not
turn on Funnel for this private-workspace example.

## Theme and cleanup

The assets mount covers `/app/public/outlands` only, never all of `/app/public`.
If you add local images, follow the image-discovery/restart behavior documented
for your Homepage release. See [settings](https://gethomepage.dev/configs/settings/)
and [custom CSS](https://gethomepage.dev/configs/custom-css-js/).

After reviewing the Compose project identity, `docker compose --env-file .env -f
compose.yaml down` removes this example's container/network. It is not a backup
or a restore; local configuration remains on disk. No cleanup command is run by
this repository's source checker.
