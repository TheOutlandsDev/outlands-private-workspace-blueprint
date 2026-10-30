# Build a private workspace with evidence at each step

This guide turns the [architecture](01-architecture.md) into a sequence that can be reviewed. The examples are fictional. A source check, a rendered page, a working login, and a successful restore answer different questions.

## 1. Write the boundary before the configuration

For each application, record its purpose, intended audience, state, credentials, route, and owner. Keep the real record private. The public design can use roles such as `catalog`, `metrics viewer`, and `application` without publishing a device list or network map.

Draw the access path and every alternate path. A Homepage link does not enforce authorization. A private network route does not replace the application's login. A restricted viewer must not expose a general upstream API or a Docker socket. Review the [access cases](03-access-and-qa.md) before putting an app behind a friendly link.

## 2. Make one reversible change

Start with the local [Homepage example](../examples/homepage/README.md). Select an image reference, resolve the Compose model, and record the exact files used. Add one fictional service entry and check its layout. Then configure a private route in your own environment, with its policy and application authorization reviewed separately.

Before changing a running service, record the current version, state location, backup method, and rollback conditions privately. If a check fails, retain the failed observation and stop. A later attempt gets a new record; it does not rewrite the earlier result.

## 3. Test claims at the layer they describe

| Claim | Useful evidence | What it does not establish |
| --- | --- | --- |
| Source is well formed | Syntax, link, schema, and static checks on the selected files | Service startup or user access |
| Example renders | Browser check of the fictional page at named viewport sizes | Native app compatibility or a physical phone result |
| Route is private | Allowed and denied network observations from authorized test identities | Application authorization |
| Owner can use the app | Native login and expected task on the intended route | Non-owner denial or recovery |
| Backup can restore | Isolated restore with expected state read back | Downgrade compatibility or owner acceptance |

Run the repository's source checks for changes to this guide. Record actual commands, scope, date, and result for an installation in a private evidence store. Keep `NOT RUN` and `BLOCKED` visible. The [fictional evidence ledger](../examples/evidence-ledger/README.md) demonstrates a small, offline way to keep these states distinct; its validator checks structure, not the truth of a claim.

## 4. Verify the user interface and recovery

Check the native interface on desktop, portrait, and landscape. Use a physical phone when the claim concerns a phone. Confirm that the intended user can complete a real task and that signed-out and unassigned users cannot reach protected data through a direct route. Inspect the response body as well as a status code. Use documented read endpoints for denial checks.

After a backup, test an isolated restore and read the expected state. Keep snapshot creation, restore testing, rollback testing, and owner acceptance as separate results. The [operations guide](05-operations.md) describes their evidence requirements.

## 5. Publish only the portable part

Build a fresh export with fictional configuration and fixtures. Preserve upstream notices. Review the exact paths and metadata before any public commit. The [publication review](22-publication-review.md) gives a repeatable selection process. A public tutorial can teach the method without carrying its operator's private record.
