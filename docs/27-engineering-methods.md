# Engineering methods for a private workspace

Build small increments that another reader can inspect and reproduce. The unit
of work is a concrete behavior, a bounded implementation, a fictional fixture,
and an honest statement of acceptance. Keep original operational material in its
private location; create public examples from invented inputs.

## Design and implement

1. State the trigger, intended result and boundary. For example: an invented
   source becomes stale, so the fictional dashboard must show stale rather than
   healthy. Define what the change cannot establish.
2. Identify interfaces and authority. A catalog link grants no app access; a
   collector reads only an approved scope; a document supplies data, never tool
   instructions. Give each module its own inputs, state and recovery path.
3. Implement the smallest useful behavior. Prefer explicit inputs, fixed output
   fields, bounded reads, no-overwrite private outputs and refusal on ambiguity.
   Optional network or host access must have a separate, explicit entry point.
4. Test a useful success case and meaningful failure cases: missing input,
   malformed state, partial coverage, unavailable service, denied access and
   failed recovery where applicable. Do not substitute mocked calls for native
   acceptance evidence.
5. Review the exact diff and notices. Keep copied or adapted components traceable
   to their primary source and license. A clean scan does not establish rights.

The [workspace planner](../tools/workspace-plan/README.md) demonstrates this method
without touching a host: strict fixture shape, dependency ordering, cycle refusal,
fixed errors and acceptance fields that cannot become successful through planning.
The [four working synthetic systems](../modules/reference-systems/README.md)
extend this approach to actual session-to-retrieval access checks, bounded source
counting, document deletion and advisory matching.
The [evidence ledger](../examples/evidence-ledger/README.md) and
[release tools](../examples/release-manifest/README.md) supply other small examples.

## Separate evidence from inference

| Observation | What it establishes | What still needs checking |
| --- | --- | --- |
| Source tests pass | Checked code behaved as the fixtures require | Native app compatibility, live settings and complete deployment. |
| Compose resolves | Selected configuration is structurally resolvable | Running services, effective binding, owner login and access denial. |
| Fresh synthetic metric | Fictional freshness behavior works | Live collector coverage, alert delivery and retention. |
| One saved file restores | That file was recovered in that exercise | Application consistency, account continuity and full recovery. |
| Offline source count | Included saved files were counted by stated rules | Authorship, excluded work, unsaved changes and full discovery. |
| Public advisory matches a version | Review may be needed | Installed configuration, reachability, exploitability and remediation. |

For each acceptance gate, privately record UTC observation time, exact software
or source revision, expected result, actual result, evidence reference and limits.
Use `NOT_RUN`, failed, partial and unverified honestly. Keep earlier failed runs
when a fix passes. The [delivery method](21-evidence-driven-delivery.md) explains
how evidence progresses from a source check to observed behavior.

## Turn private work into a public example

Write an invented fixture from the general interface and method. Avoid exporting
real configuration and trying to remove every sensitive field afterward. Exclude
real host and account identities, network topology, model inventories, data,
security findings, backup providers and destinations, and operational timestamps
that identify private activity. Check filenames, links, screenshots, metadata,
history, commit messages and PR text as well as code.

Before the first public branch upload, freeze an exact file selection and hashes,
run the [pre-upload review aid](../tools/preupload-check/README.md), run relevant
source tests, and complete manual privacy, synthetic-data, provenance, rights,
diff and destination review. Public branches expose their contents before CI.
Use only safe filenames and generic naming combinations for bounded provenance
searches. No indexed match is limited search evidence, not ownership clearance.
Keep manifests, private terms, completed worksheets and receipts outside Git.

After uploading the reviewed bytes, inspect the remote file list and compare
content hashes, wait for required checks, and merge through the protected PR
path. Verify the resulting default branch and distinguish hosted results from
reader-host acceptance. Preserve the existing visibility and license. Follow
the [publication review](22-publication-review.md) for the complete boundary.
