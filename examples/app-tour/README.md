# OUTLANDS · Fictional app tour

Thirteen original static pages let beginners inspect the design before touching an app. They do not reproduce vendor interfaces. All labels, statuses and values are invented. No private app source or configuration is included.

## Run

From the repository root, with Python 3.9+:

```sh
python3 -I -B examples/app-tour/serve_demo.py --port 8766
```

Open `http://127.0.0.1:8766/`. Choose an example using the visible navigation. If the port is occupied, choose another `--port` value, or use `--port 0` and open the printed URL. Press Ctrl+C to stop. There are no dependencies to install and no Docker daemon, APIs, model calls or identity service.

The server binds to loopback only, validates Host, serves an exact route allowlist, rejects unknown/query/encoded aliases, and supports only GET/HEAD. It logs no request data and writes no application state. It supplies a restrictive content-security policy. These are properties of the local fixture server, not an owner-only authentication implementation. Anyone with access to the local process/browser may view its fictional pages.

## Files and customization

Each `.html` file is a self-contained original layout using `tour.css` and `wall.svg`. Edit invented text and reload to experiment. No JavaScript, forms, external fonts or remote assets are used. The CSS targets only these fixtures. Do not inject it into an unreviewed native app or expose this development server to a network.

See the [walkthrough index](../../docs/07-app-walkthroughs.md) for native setup paths, sample configs, access checks and rollback. Schema snippets for original portals/fleet/Git/learning/local tools are teaching contracts, not complete deployable services. Vendor snippets are partial configs, deliberately containing non-resolving example destinations. No complete multi-app stack is installed here.
