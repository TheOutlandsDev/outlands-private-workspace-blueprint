# Working synthetic systems

Four runnable reference systems extend the [workspace blueprint](../../docs/25-systems-blueprint.md):
an identity gate, source inventory, lexical retrieval, and advisory review. They
use the Python standard library, invented accounts/documents/products, and
explicit entry points. The identity gate passes its server-side session role to
the retrieval engine; request headers cannot select that role.

## Open the integrated portal

```sh
python3 -I -B modules/reference-systems/run.py workspace --serve
```

Open the printed loopback URL, sign in with a fictional role, and follow the
[workspace walkthrough](WORKSPACE.md). Inventory, retrieval and advisory views
share the session boundary; owner controls change synthetic states and delete
documents from memory. Reader restrictions are enforced at each endpoint.
Stop with Ctrl+C. This command never accepts real roots, data sources or accounts.

## Setup and first run

Use Linux, Python 3.10+ and a downloaded checkout. No package installation,
Docker daemon, cloud account, model or private configuration is needed. From
the repository root:

```sh
python3 -I -B modules/reference-systems/run.py demo
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_*.py'
```

The demo runs identity/session checks in memory, scans only the checked-in
invented source tree, searches and deletes invented documents, and matches
invented advisory ranges. It opens no network listener and writes no files.
The HTTP integration tests separately open a temporary `127.0.0.1` listener
and close it afterward. A sandbox that forbids sockets can run the offline demo;
it must not report the HTTP tests as passed without running them.

| System | Working implementation | Setup and limits |
| --- | --- | --- |
| Identity | Password verification, opaque expiring sessions, role checks, logout revocation, CSRF and origin checks; loopback HTTP integration with retrieval | [Identity guide](IDENTITY.md) |
| Source inventory | Explicit-root, bounded saved-file scanner; separate code/configuration/prose counts; private no-overwrite reports | [Inventory guide](INVENTORY.md) |
| Retrieval | Admission, fixed-size chunks, deterministic lexical ranking, authorization before ranking, source references and deletion | [Retrieval guide](RETRIEVAL.md) |
| Advisory review | Exact product IDs, introduced-inclusive/fixed-exclusive version ranges, freshness and review candidates | [Advisory guide](ADVISORIES.md) |

The [launcher](run.py) imports only this reviewed source directory; it does not
add the caller's current directory to module lookup. [Shared I/O](runtime_io.py)
rejects duplicate JSON keys, nonfinite numbers, links and oversized input, and
creates private reports without overwrite. Each system has its own tests.

## What the working reference establishes

`SYNTHETIC_RUNTIME` in the planner means the code runs with invented fixtures.
It does not mean a production identity provider, full RAG application, live
inventory service or vulnerability scanner is deployed. No real system is
discovered or contacted by the default demo. Only the inventory command has an
explicit opt-in path for a reader-owned private source root.

Keep filled configuration, actual roots, credentials, completed acceptance,
document collections, product inventories and operational reports outside Git.
Do not route the identity demo through a proxy, LAN binding, tunnel or private
entry service: its credentials are public and it uses local HTTP. A real
identity integration retains its separate provider, TLS, account, recovery and
deployment review described in [the identity walkthrough](../../docs/11-identity.md).

## Upgrade, state and rollback

Keep a known working source revision and run the offline and HTTP tests before
switching an isolated demo. These systems install no service or scheduler.
Identity sessions and the retrieval index live in memory; stopping the process
clears them. Restarting rebuilds only the original fictional fixture; a deletion
is not persistent across a new demo process. Inventory reports are independent
private artifacts; keep prior reports instead of overwriting them. Advisory
review changes no asset or package. Roll back the source checkout, then rerun
the tests. Do not touch existing native app accounts, data or routes.

Use the [setup sequence](../../docs/26-workspace-setup.md) for the existing
Compose modules and the [engineering method](../../docs/27-engineering-methods.md)
for a future separately qualified integration. A reader's real acceptance
worksheet remains `NOT_RUN` until supported by that reader's evidence.
