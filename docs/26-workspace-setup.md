# Build the workspace in stages

Start with a downloaded checkout and an isolated reader-owned Linux test host.
The public files are templates; completed configuration, acceptance records and
operational evidence belong in a separate private workspace. The repository
does not select current image versions, install a stack, or migrate a server.

## 1. Inspect the source and choose a profile

These commands read public files only. They do not need Docker or an account:

```sh
python3 -I -B scripts/check_public_source.py
python3 -I -B tools/workspace-plan/workspace_plan.py minimal
python3 -I -B tools/workspace-plan/workspace_plan.py workspace
python3 -I -B tools/workspace-plan/workspace_plan.py extended
```

Choose one profile; running all three only previews their different plans.
`minimal` orders foundation, AI and recovery. `workspace` adds fictional metrics
and a catalog. `extended` includes optional access and working synthetic systems.
Every emitted acceptance gate starts at `NOT_RUN`. `SYNTHETIC_RUNTIME` means
reference code runs with invented fixtures, not an accepted real deployment.

## 2. Prepare the host and private copy

Follow [Docker's supported-platform installation guide](https://docs.docker.com/engine/install/)
and review its [daemon security model](https://docs.docker.com/engine/security/).
Choose images and architecture-specific immutable digests privately after checking
upstream support, release notes and licenses. Keep a record of the exact software
snapshot with your private acceptance worksheet. A successful source check says
nothing about available memory, storage, ports or the selected Docker context.

The [reader quick-start](../hosts/server-01/QUICKSTART.md) contains the actual
read-only local-context preflight and private-copy preparation commands. Use its
new-directory helper before filling any secrets. It refuses an existing
destination; inspect partial copies privately instead of overwriting them.

## 3. Bring up one runtime module at a time

| Order | Setup guide | Evidence before continuing |
| --- | --- | --- |
| Foundation | [Docker host](../modules/foundation/docker-host/README.md) | Intended local context, bounded smoke check and retained recovery access. |
| AI | [Ollama + Open WebUI](../modules/ai/ollama-open-webui/README.md) | Loopback WebUI, internal API, owner login, signup denial and signed-out denial; model inference separately if selected. |
| Observability, optional | [Synthetic metrics](../modules/observability/synthetic-metrics/README.md) | Native login and invented fresh, stale, unavailable and recovered states. |
| Catalog, optional | [Homepage](../modules/catalog/homepage/README.md) | Native page loads; each private destination passes its own access checks. |
| Private entry, optional | [Access trial](../modules/access/private-entry/README.md) | Allowed and denied network identities plus allowed and denied application sessions. |
| Recovery | [Disposable rehearsal](../staging/server-01/README.md) and [operations](05-operations.md) | Consistent state capture, isolated restore, retained data and login, then documented cleanup of the disposable project. |

Follow the module-specific Compose commands in the private copy. Review resolved
configuration privately; it can contain secrets. Do not connect an unqualified
module to a production network or data store. The existing
[assembly worksheet](../hosts/server-01/assembly.example.json) defines the runtime
gates; the planner adds no new deployment authority.

Upstream references checked for this guide: [Open WebUI quick-start](https://docs.openwebui.com/getting-started/quick-start/)
and [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).
Upstream defaults can change. Review their current requirements and preserve this
blueprint's explicit local binding, per-app authorization and separate denial tests.

## 4. Run the four synthetic systems

The [working reference systems](../modules/reference-systems/README.md) implement
identity sessions, bounded source inventory, admitted lexical retrieval and
advisory range review. They use Linux and Python 3.10+, with no Docker or model
requirement. The planner dependencies describe a learning sequence rather than
software prerequisites. From the repository root:

```sh
python3 -I -B modules/reference-systems/run.py demo
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_*.py'
```

Follow each linked system guide for setup, inputs, refusal behavior, state and
rollback. The separate identity demo binds only loopback and uses public
fictional credentials; keep it isolated. Its HTTP tests verify actual owner/reader
access and retrieval filtering. Default commands read only public fixtures.
Real provider login, native SSO, document ingestion and advisory feeds still need
separate private adapters and deployment review. Only the inventory tool offers
an explicit reader-owned private-root scan with a private no-overwrite report.

## 5. Update and roll back deliberately

Record the working image digests, configuration revision, state format and private
recovery evidence before changing one project. Review migration and downgrade
support upstream. Rehearse the candidate with a consistent copy of disposable
state; check access, denial, persistence and restoration. A process being up is
only one observation.

If acceptance fails, stop that project's change and retain the failure record.
Restore the known working configuration and compatible state using the rehearsed
procedure. Reverting an image alone may not reverse a database migration. Verify
login, retained records and denied access after recovery. Keep persistent volumes
unless their deliberate disposal is part of the isolated rehearsal; never use a
volume-delete command as a general rollback step.

Use the [engineering methods](27-engineering-methods.md) to record outcomes and
prepare any later public explanation. No real host update, route, account or
restore is performed by this guide or the offline planner.
