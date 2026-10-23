# Operate and recover deliberately

Treat the workspace as a collection of services with separate state, access rules, and failure modes. A catalog can load while a linked app is unavailable. A health endpoint can pass while login, a widget, a mobile route, or recovery still fails.

## Keep a private service record

Maintain a private record for each component: image pin, configuration location, state volumes, native sign-in, authorized audience, private route, health signal, update source, backup procedure, and recovery dependencies. None of those records belongs in a public tutorial if it contains operational identifiers.

Store real secrets outside source control and grant them only to the services that require them. Compose supports per-service file-based secrets; applications must support the corresponding file input to use them. This mechanism still requires protected source files and a private host. [Docker Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/)

Keep public examples and private deployment files in separate working directories. An ignore rule is a useful guard, but review tracked files and Git history before publication. Scrub logs and exports deliberately; renaming a file or deleting its current copy does not remove previous committed content.

## Observe freshness and limits

For Fleet, retain only fields needed to answer an operational question. Use separate timestamps for inventory collection and metric samples. CPU, available memory, disk usage, and uptime must identify the host and time window they describe. Test disk calculations against a known filesystem and define which mounts count. Node Exporter exposes host measurements; Prometheus querying supplies the selection and aggregation logic. [Node Exporter guide](https://prometheus.io/docs/guides/node-exporter/), [Prometheus query basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)

Display **UNKNOWN** when source data is missing and **STALE** when it exceeds the chosen age limit. An offline Tailscale device can remain in inventory. A recent metrics sample is not proof that an application login works. Keep telemetry viewers and upstream endpoints independently protected. [Tailscale CLI inventory](https://tailscale.com/docs/reference/tailscale-cli), [Prometheus security model](https://prometheus.io/docs/operating/security/)

## Back up state, then prove recovery

Define a consistent snapshot method for each app's database and files. A live directory copy may not be application-consistent. Include configuration, state, and the information needed to retrieve the correct image version. Keep secrets in protected recovery storage rather than in the public repository. Grafana's backup guide covers configuration, plugin data, and databases, and calls out stopping Grafana for an integrity-preserving SQLite copy. [Grafana backups](https://grafana.com/docs/grafana/latest/administration/back-up-grafana/)

Use these labels honestly:

| Label | Evidence required |
| --- | --- |
| Backup planned | Written scope and procedure |
| Snapshot created | Snapshot exists, with time, size, and integrity evidence |
| Restore tested | Isolated restore starts and the expected state is readable |
| Rollback tested | Previous compatible app version and state work after the planned reversal |
| Recovery accepted | Owner checks critical data and workflows against written criteria |

A checksum verifies bytes against a recorded digest; it does not prove that an app can restore them. A snapshot that exists has not yet passed a restore drill. Restoring a backup has not automatically proved downgrade compatibility after a database migration.

## Change one layer at a time

1. Record the current pin, state backup, route, and acceptance results privately.
2. Read the component's release notes, including migrations and downgrade limits.
3. Apply the change in an isolated copy first.
4. Repeat the affected local, owner login, denial, direct-route, widget, and real phone checks.
5. Verify the planned rollback on that isolated copy before relying on it.
6. Schedule the real change only when its recovery path and owner impact are understood.

A Serve background configuration can persist across a reboot. Review its existing state before changing it and remove only the route you own using the current CLI syntax. Avoid a blanket reset on a shared node. [Serve CLI lifecycle](https://tailscale.com/docs/reference/tailscale-cli/serve)

## An activity log that states what happened

Record UTC time, the component, intended change, actual action, evidence, and result. Use separate entries for static validation, local runtime, remote access, Browser QA, real phone testing, and recovery. Never convert a tutorial, synthetic fixture, blocked check, or planned gate into a production success claim.

This public blueprint ends at instructions and sanitized examples. Your own deployment becomes operational only after you run and record the relevant checks in your environment.
