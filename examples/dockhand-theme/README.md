# Dockhand cyberpunk theme example

Start with the [beginner walkthrough](../../docs/06-dockhand-cyberpunk.md).
This directory contains an original static mockup, a small CSS adapter and
**nondeployable** Nginx design fragments. It includes no Dockhand image, vendor
application code, credentials, Docker socket, real inventory or authentication
service.

From the repository root, with Python 3.9 or newer:

```sh
python3 -I -B examples/dockhand-theme/serve_demo.py
```

Open the loopback URL printed by the command. With the default port it is
`http://127.0.0.1:8765/demo/`. Keep the terminal open and press Ctrl+C to stop.
If that port is busy, add `--port 8766`. If your Python executable is named
`python` on Windows, use that command instead of `python3`.

The preview is labeled **ILLUSTRATIVE MOCKUP**. Its six containers and metrics
are invented; the refresh and search controls are disabled deliberately. It
has no scripts or app connections, so no live stats should be expected.

| File | Purpose |
|---|---|
| `theme/netwall.css` | Original CSS adapter; version-specific native selectors need review. |
| `theme/assets/netwall.svg` | Original red wall, derived from the blueprint's public SVG. |
| `theme/assets/mark.svg` | Original OUTLANDS mark from this blueprint. |
| `demo/index.html` and `demo/base.css` | Original fixture layout; not Dockhand's application or vendor styles. |
| `serve_demo.py` | Fixed-file loopback preview server; no directory listing or API. |
| `nginx-theme-assets.example.conf` | Exact asset-path pattern with a placeholder owner check that denies everyone. |
| `nginx-html-overlay.example.inc` | HTML-only stylesheet insertion pattern for an existing protected proxy. |

A real installation must supply its own owner authentication, reviewed native
routes, image selection, data protection, cache strategy and rollback plan.
The proxy fragments do not configure these. They are not a complete read-only
Docker gateway. See the walkthrough before adapting them.

Original example materials use the repository's [MIT license](../../LICENSE).
Dockhand software and branding retain their own upstream terms.

## Clean demo captures

Both captures are labeled ILLUSTRATIVE MOCKUP and use invented data.

![Desktop fictional theme demo](../../assets/dockhand-demo-desktop.jpg)

<img src="../../assets/dockhand-demo-portrait.jpg" alt="Portrait fictional theme demo" width="390">
