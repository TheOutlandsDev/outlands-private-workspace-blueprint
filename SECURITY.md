# Security reporting

This repository is a guide and a small local example, not a managed access
service. It cannot attest another person's tailnet, app permissions or backups.

If GitHub private vulnerability reporting is enabled, use it for a finding that
could expose credentials, private access or control APIs. Otherwise open a
minimal issue asking for a private reporting channel, without publishing the
sensitive details. Do not include a working credential or private endpoint.

An allowlist should fail closed after an upstream change. A read-only Docker
socket mount does not make the Docker API read-only. A link on Homepage does not
limit who can open its destination. Tailnet membership is not an owner role.
Keep these boundaries explicit and test them for your own installation.
