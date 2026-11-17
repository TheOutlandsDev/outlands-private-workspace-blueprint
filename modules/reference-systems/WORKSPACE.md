# Integrated synthetic workspace

One local portal connects identity sessions, source inventory, document retrieval
and advisory review. Every input comes from the checked-in invented fixtures.
It has no private connector, real-root selector, production account or live feed.

## Optional durable synthetic state

Use the [state and recovery guide](STATE.md) to initialize a new owner-private
state directory outside Git, then add `--state-dir "$PRIVATE_STATE_DIR"` to the
serve command. Active document deletions and source-state changes then survive
restart. Sessions remain ephemeral. Backup, restore, upgrade, rollback and reset
are explicit offline commands; prior generations are retained.

## Start and stop

Use Linux and Python 3.10+ in a downloaded checkout. From the repository root:

```sh
python3 -I -B modules/reference-systems/run.py workspace --serve
```

Open the exact `http://127.0.0.1:` URL printed in the terminal. The process
chooses an unused local port. To select a fixed local port, append `--port 8788`.
No package installation, Docker or model is needed. Stop with Ctrl+C; the server
closes its listener and its sessions disappear. In default memory-only mode, document/scenario changes
also disappear; explicit persistent mode retains them.

Sign in as `fictional-owner` or `fictional-reader`, using the public fixture
password `synthetic-only`. The owner and reader share one synthetic workspace,
with different server-enforced access. The page labels all data as invented.

| Capability | Owner | Reader | Signed out |
| --- | --- | --- | --- |
| Aggregate invented inventory and its state | Allowed | Allowed | Denied |
| Search documents permitted to the session role | Allowed | Allowed | Denied |
| Owner-only document text or identifiers | Allowed | Omitted from search and page | Denied |
| Advisory details and document administration list | Allowed | Denied | Denied |
| Change fixture source state or delete a document from active state | Allowed with session CSRF and exact Origin | Denied, even with a valid reader CSRF value | Denied |

Reader pages omit administrative forms and owner-only data. The endpoints enforce
the same rules independently; hiding controls is not the authorization mechanism.
Roles come from the session, not query fields or forwarded identity headers.

## Try the acceptance walkthrough

1. Sign in as owner. The overview shows invented code/configuration/prose counts,
   three permitted documents and one unconfirmed advisory range candidate.
2. Search `recovery`. The fictional owner note is returned with its source ID and
   an untrusted-text label. An unmatched term shows `EMPTY` and no source IDs.
3. Use Owner controls to select `stale`, then `unavailable`. Stale data stays
   visibly labeled. Unavailable sources show no inventory or candidate counts;
   retrieval remains independently available. Select `fresh` to recover.
4. Delete `fictional-owner-note` with the owner form, then search `recovery`
   again. It is absent from results, document administration and the count.
   In memory-only mode, restarting restores the fixture. In persistent mode,
   active deletion survives restart; older generations and snapshots retain prior data.
5. Sign out, sign in as reader, and inspect the overview. Inventory and permitted
   search remain; advisory details show `DENIED` and Owner controls are absent.
   Directly opening `/workspace/advisories` also denies access. With a fresh
   process, reader search cannot reveal the still-existing owner note.
6. Sign out again. Protected HTML and API routes deny the old session. Expired
   and forged sessions are also refused. Check desktop and a narrow viewport;
   viewport simulation does not establish physical-device acceptance.

All freshness labels use the fixed fictional clock. Choosing a scenario simulates
source freshness/availability; it does not change or measure a real service.

## HTTP surface

| Route | Purpose |
| --- | --- |
| `GET /` | Sign-in page or role-filtered overview. |
| `GET /workspace.css` | One fixed reviewed stylesheet; no arbitrary file serving. |
| `GET /workspace/search?q=lamp` | Escaped HTML results filtered by session role. |
| `GET /workspace/advisories` | Owner-only fictional advisory table. |
| `GET /api/summary` | Role-filtered synthetic projection; reader advisory section contains only `DENIED`. |
| `GET /api/inventory` | Aggregate synthetic inventory and source state. |
| `GET /api/search?q=lamp` | Permitted JSON extracts; `/search` remains the existing JSON alias. |
| `GET /api/advisories`, `GET /api/documents` | Owner-only details and document IDs. |
| `POST /admin/scenario` | Owner-only `scenario` plus session `csrf`; fixed scenario values only. |
| `POST /admin/delete` | Owner-only `source_id` plus session `csrf`; active removal, durably committed when persistent mode is selected. |
| `/login`, `/session`, `/logout`, `/private` | Existing [identity/session contract](IDENTITY.md). |

Mutations require the exact loopback Host/Origin, an active owner session and its
CSRF value. GET cannot perform administrative changes. Missing, foreign and
`null` origins remain refused. `Referrer-Policy: same-origin` preserves browser
form Origin behavior without sending referrers cross-origin; `no-referrer` caused
legitimate form navigation to send a null Origin in browser testing. See the
[Origin](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Origin)
and [Referrer-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy)
references. Responses disable caching, and CSP permits only the same-origin
stylesheet and forms. There is no JavaScript or external asset load.

Query/source text is HTML-escaped. Error responses do not echo credentials or
exceptions. Requests are not logged. The portal exposes no scanner command, file
upload, root-path input or advisory-feed URL; the standalone opt-in private scanner
retains its [separate guide](INVENTORY.md).

## Tests and maintenance

```sh
python3 -I -B modules/reference-systems/run.py workspace --demo
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_workspace.py'
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_*.py'
```

The summary demo uses no socket and writes no file. HTTP tests create temporary
loopback listeners and verify direct reader attacks, CSRF/origin refusal, expiry,
logout, filtered counts/IDs, deletion, source states, fixed file scope and escaping.
The required CI runs the complete suite. Browser checks separately establish
actual form submission and visible states; HTTP client tests alone did not catch
the earlier browser Origin/referrer interaction.

Keep a known working source revision. Stop the owned demo before switching it,
rerun tests, and start a fresh process. In memory-only mode this resets sessions, deletions and fixture
states together. Persistent mode clears sessions while preserving committed data;
use the [explicit state recovery/reset commands](STATE.md) for that mode. Reverting a source change affects this demo only; it is not a
real application-data restore. No service or schedule is installed.

The demo stays isolated on loopback HTTP with public credentials. It is not a
production authentication boundary, native SSO integration, production document
store or live security console. Keep real settings, data, inventories, reports
and deployment acceptance in a separate private workspace.
