# Contributing

Start with the problem: what did you try, what did you expect, and what happened?
Include the relevant upstream app/version and a small fictional example when
possible. Mark whether a result came from source review, a local app, a real
phone, or a restore exercise.

Keep examples private by design. Replace account names, domains, device IDs and
addresses with reserved examples. Do not attach live logs, tokens, cookies,
backup payloads, configuration exports, database files or screenshots containing
private inventory. Do not name an operator's backup provider, account, storage
location, bucket, endpoint, or recovery path. Reproduce the issue using a minimal
example instead.

For code or documentation changes, run `python3 -I -B scripts/check_public_source.py`
from the repository root, verify relative links, and state what you did not test.
For changes to the fictional evidence ledger, also run
`python3 -I -B -m unittest discover -s examples/evidence-ledger -p 'test_*.py'`.
Do not add an automatic installer or expand a proxy/API policy without describing
the exact behavior, failure handling and rollback procedure.

Original contributions use the repository's MIT license. Upstream software and
branding are not relicensed by this repository.
